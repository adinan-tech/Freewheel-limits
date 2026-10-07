"""Small OCI SDK boundary for the limit checker."""

from .checker import Availability, CheckError, Definition, LimitValue
from .config import Config, Monitor


class OciLimitsGateway:
    def __init__(self, client, oci_module, identity_client=None):
        self.client = client
        self.oci = oci_module
        self.identity_client = identity_client

    @classmethod
    def create(cls, region: str, auth: str, config_file: str | None, profile: str, home_region: str | None = None):
        try:
            import oci
        except ImportError as exc:
            raise CheckError("OCI Python SDK is required; install requirements.txt") from exc

        options = {
            "timeout": (10, 30),
            "retry_strategy": oci.retry.DEFAULT_RETRY_STRATEGY,
        }
        try:
            if auth == "resource-principal":
                signer = oci.auth.signers.get_resource_principals_signer()
                client = oci.limits.LimitsClient({"region": region}, signer=signer, **options)
                identity_client = oci.identity.IdentityClient({"region": home_region or region}, signer=signer, **options)
            else:
                if config_file:
                    credentials = oci.config.from_file(file_location=config_file, profile_name=profile)
                else:
                    credentials = oci.config.from_file(profile_name=profile)
                credentials["region"] = region
                oci.config.validate_config(credentials)
                client = oci.limits.LimitsClient(credentials, **options)
                identity_credentials = dict(credentials)
                identity_credentials["region"] = home_region or region
                identity_client = oci.identity.IdentityClient(identity_credentials, **options)
        except (oci.exceptions.ClientError, OSError, ValueError) as exc:
            raise CheckError(f"cannot initialize OCI access: {type(exc).__name__}") from exc
        return cls(client, oci, identity_client)

    def _list(self, method, *args, **kwargs):
        try:
            return self.oci.pagination.list_call_get_all_results(method, *args, **kwargs).data
        except self.oci.exceptions.ServiceError as exc:
            raise CheckError(f"OCI API error {exc.status} ({exc.code})") from exc
        except self.oci.exceptions.RequestException as exc:
            raise CheckError("OCI API request failed") from exc

    def definitions(self, config: Config, monitor: Monitor) -> list[Definition]:
        args = {"service_name": monitor.service_name, "name": monitor.limit_name}
        items = self._list(self.client.list_limit_definitions, config.tenancy_id, **args)
        return [
            Definition(item.name, item.scope_type, item.is_resource_availability_supported)
            for item in items
        ]

    def values(self, config: Config, monitor: Monitor, scope_type: str) -> list[LimitValue]:
        args = {"name": monitor.limit_name, "scope_type": scope_type}
        if monitor.availability_domain:
            args["availability_domain"] = monitor.availability_domain
        items = self._list(
            self.client.list_limit_values,
            config.tenancy_id,
            monitor.service_name,
            **args,
        )
        return [
            LimitValue(item.name, item.scope_type, item.availability_domain, item.value)
            for item in items
        ]

    def availability(self, config: Config, monitor: Monitor) -> Availability:
        args = {}
        if monitor.availability_domain:
            args["availability_domain"] = monitor.availability_domain
        try:
            response = self.client.get_resource_availability(
                monitor.service_name,
                monitor.limit_name,
                config.tenancy_id,
                **args,
            )
        except self.oci.exceptions.ServiceError as exc:
            raise CheckError(f"OCI API error {exc.status} ({exc.code})") from exc
        except self.oci.exceptions.RequestException as exc:
            raise CheckError("OCI API request failed") from exc
        data = response.data
        used = data.fractional_usage if data.fractional_usage is not None else data.used
        return Availability(used, data.available)

    def policy_count(self, config: Config) -> int:
        if self.identity_client is None:
            raise CheckError("OCI Identity client is not configured")
        try:
            compartments = self._list(
                self.identity_client.list_compartments,
                config.tenancy_id,
                compartment_id_in_subtree=True,
                lifecycle_state="ACTIVE",
            )
            compartment_ids = [config.tenancy_id, *(item.id for item in compartments)]
            return sum(len(self._list(self.identity_client.list_policies, compartment_id)) for compartment_id in compartment_ids)
        except CheckError:
            raise
