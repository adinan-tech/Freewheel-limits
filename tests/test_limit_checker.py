import unittest
from types import SimpleNamespace
import json

from limit_checker.checker import Availability, CheckError, Definition, LimitValue, check_all
from limit_checker.config import ConfigError, parse_config
from limit_checker.oci_gateway import OciLimitsGateway
from function.func import run_check


def sample_config(**changes):
    data = {
        "region": "eu-frankfurt-1",
        "tenancy_id": "ocid1.tenancy.oc1..example",
        "subscription_id": None,
        "check_schedule_utc": "0 * * * *",
        "email_recipients": ["ops@example.com"],
        "monitors": {
            "compute": {
                "service_name": "compute",
                "limit_name": "standard3-core-count",
                "availability_domain": "eu-frankfurt-1-AD-1",
                "warning_percent": 80,
            }
        },
    }
    data.update(changes)
    return parse_config(data)


class FakeGateway:
    def __init__(self, *, scope="AD", supported=True, hard=100, used=79, available=21):
        self.scope = scope
        self.supported = supported
        self.hard = hard
        self.used = used
        self.available = available
        self.calls = []

    def definitions(self, config, monitor):
        self.calls.append("definitions")
        return [Definition(monitor.limit_name, self.scope, self.supported)]

    def values(self, config, monitor, scope_type):
        self.calls.append("values")
        return [LimitValue(monitor.limit_name, scope_type, monitor.availability_domain, self.hard)]

    def availability(self, config, monitor):
        self.calls.append("availability")
        return Availability(self.used, self.available)


class CheckerTests(unittest.TestCase):
    def test_function_entrypoint_uses_same_configuration(self):
        config_json = json.dumps({
            "region": "eu-frankfurt-1",
            "tenancy_id": "ocid1.tenancy.oc1..example",
            "subscription_id": None,
            "check_schedule_utc": "0 * * * *",
            "email_recipients": ["ops@example.com"],
            "monitors": {
                "compute": {
                    "service_name": "compute",
                    "limit_name": "standard3-core-count",
                    "availability_domain": "eu-frankfurt-1-AD-1",
                    "warning_percent": 80,
                }
            },
        })
        payload = run_check(config_json, FakeGateway(hard=100, used=80, available=20))
        self.assertEqual(payload["results"][0]["status"], "WARNING")

    def test_warning_boundary_and_current_hard_limit(self):
        config = sample_config()
        gateway = FakeGateway()
        result = check_all(config, gateway)[0]
        self.assertEqual(result.status, "OK")
        self.assertEqual(result.usage_percent, 79)
        gateway.used = 80
        self.assertEqual(check_all(config, gateway)[0].status, "WARNING")
        gateway.hard = 200
        self.assertEqual(check_all(config, gateway)[0].status, "OK")
        self.assertEqual(gateway.calls[:3], ["definitions", "values", "availability"])

    def test_missing_and_zero_limit_are_errors(self):
        for hard in (None, 0):
            with self.subTest(hard=hard):
                result = check_all(sample_config(), FakeGateway(hard=hard))[0]
                self.assertEqual(result.status, "ERROR")
                self.assertIn("hard limit", result.error)

    def test_unsupported_and_missing_usage_are_errors(self):
        self.assertEqual(check_all(sample_config(), FakeGateway(supported=False))[0].status, "ERROR")
        result = check_all(sample_config(), FakeGateway(used=None))[0]
        self.assertEqual(result.status, "ERROR")
        self.assertIn("used and available", result.error)

    def test_scope_and_api_error_are_reported(self):
        result = check_all(sample_config(), FakeGateway(scope="REGION"))[0]
        self.assertEqual(result.status, "ERROR")
        self.assertIn("omitted", result.error)

        class FailingGateway(FakeGateway):
            def availability(self, config, monitor):
                raise CheckError("OCI API error 503 (ServiceUnavailable)")

        result = check_all(sample_config(), FailingGateway())[0]
        self.assertEqual(result.status, "ERROR")
        self.assertIn("503", result.error)

    def test_regional_storage_limit_needs_no_ad(self):
        config = sample_config(monitors={
            "storage": {
                "service_name": "block-volume",
                "limit_name": "backup-count",
                "availability_domain": None,
                "warning_percent": 75,
            }
        })
        result = check_all(config, FakeGateway(scope="REGION", hard=100, used=75, available=25))[0]
        self.assertEqual(result.status, "WARNING")
        self.assertEqual(result.scope_type, "REGION")

    def test_invalid_customer_input_is_rejected(self):
        with self.assertRaisesRegex(ConfigError, "placeholder"):
            sample_config(region="<oci-region>")
        bad = {
            "example": {
                "service_name": "compute",
                "limit_name": "standard3-core-count",
                "availability_domain": None,
                "warning_percent": 100,
            }
        }
        with self.assertRaisesRegex(ConfigError, "warning_percent"):
            sample_config(monitors=bad)


class AdapterTests(unittest.TestCase):
    def test_sdk_fields_and_scope_are_mapped(self):
        class Client:
            def list_limit_definitions(self, *args, **kwargs):
                self.definitions_args = (args, kwargs)
                return SimpleNamespace(data=[SimpleNamespace(
                    name="standard3-core-count", scope_type="AD",
                    is_resource_availability_supported=True,
                )])

            def list_limit_values(self, *args, **kwargs):
                self.values_args = (args, kwargs)
                return SimpleNamespace(data=[SimpleNamespace(
                    name="standard3-core-count", scope_type="AD",
                    availability_domain="eu-frankfurt-1-AD-1", value=120,
                )])

            def get_resource_availability(self, *args, **kwargs):
                self.availability_args = (args, kwargs)
                return SimpleNamespace(data=SimpleNamespace(
                    used=96, fractional_usage=95.5, available=24,
                ))

        class Pagination:
            @staticmethod
            def list_call_get_all_results(method, *args, **kwargs):
                return method(*args, **kwargs)

        sdk = SimpleNamespace(pagination=Pagination, exceptions=SimpleNamespace(ServiceError=Exception))
        client = Client()
        gateway = OciLimitsGateway(client, sdk)
        result = check_all(sample_config(), gateway)[0]
        self.assertEqual(result.status, "OK")
        self.assertEqual(result.hard_limit, 120)
        self.assertEqual(result.used, 95.5)
        self.assertEqual(client.values_args[1]["availability_domain"], "eu-frankfurt-1-AD-1")
        self.assertEqual(client.availability_args[0][2], "ocid1.tenancy.oc1..example")

    def test_oci_404_is_a_per_monitor_error(self):
        class ServiceError(Exception):
            status = 404
            code = "NotFound"

        class Client:
            def list_limit_definitions(self, *args, **kwargs):
                return SimpleNamespace(data=[SimpleNamespace(
                    name="standard3-core-count", scope_type="AD",
                    is_resource_availability_supported=True,
                )])

            def list_limit_values(self, *args, **kwargs):
                return SimpleNamespace(data=[SimpleNamespace(
                    name="standard3-core-count", scope_type="AD",
                    availability_domain="eu-frankfurt-1-AD-1", value=100,
                )])

            def get_resource_availability(self, *args, **kwargs):
                raise ServiceError()

        class Pagination:
            @staticmethod
            def list_call_get_all_results(method, *args, **kwargs):
                return method(*args, **kwargs)

        sdk = SimpleNamespace(pagination=Pagination, exceptions=SimpleNamespace(ServiceError=ServiceError))
        result = check_all(sample_config(), OciLimitsGateway(Client(), sdk))[0]
        self.assertEqual(result.status, "ERROR")
        self.assertIn("404", result.error)


if __name__ == "__main__":
    unittest.main()
