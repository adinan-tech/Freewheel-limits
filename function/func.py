"""OCI Functions entry point for a scheduled, read-only limit check."""

import json
import os
from datetime import datetime, timezone

from limit_checker.checker import check_all
from limit_checker.config import parse_config
from limit_checker.oci_gateway import OciLimitsGateway


def run_check(config_json: str, gateway=None) -> dict:
    config = parse_config(json.loads(config_json))
    if gateway is None:
        gateway = OciLimitsGateway.create(config.region, "resource-principal", None, "DEFAULT", config.home_region)
    results = check_all(config, gateway)
    return {"results": [result.to_dict() for result in results]}


def publish_metrics(results: list[dict], region: str, compartment_id: str, client=None) -> None:
    """Publish one usage-percent data point per configured limit."""
    try:
        import oci
        if client is None:
            signer = oci.auth.signers.get_resource_principals_signer()
            client = oci.monitoring.MonitoringClient(
                {"region": region},
                signer=signer,
                service_endpoint=f"https://telemetry-ingestion.{region}.oraclecloud.com",
                timeout=(10, 30),
                retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY,
            )
        metric_data = []
        for result in results:
            if result["usage_percent"] is None:
                continue
            metric_data.append(oci.monitoring.models.MetricDataDetails(
                namespace="limit_warnings",
                compartment_id=compartment_id,
                name="LimitUsagePercent",
                dimensions={"monitor": result["monitor"]},
                datapoints=[oci.monitoring.models.Datapoint(
                    timestamp=datetime.now(timezone.utc),
                    value=result["usage_percent"],
                )],
            ))
        if metric_data:
            client.post_metric_data(oci.monitoring.models.PostMetricDataDetails(metric_data=metric_data))
    except Exception as exc:
        raise RuntimeError("could not publish limit usage metrics") from exc


def handler(ctx, data=None):
    from fdk import response

    config_json = os.environ["LIMIT_CHECKER_CONFIG"]
    payload = run_check(config_json)
    config = json.loads(config_json)
    publish_metrics(payload["results"], config["region"], os.environ["METRIC_COMPARTMENT_ID"])
    print(json.dumps(payload), flush=True)
    if any(result["status"] == "ERROR" for result in payload["results"]):
        raise RuntimeError("one or more configured limits could not be checked")
    return response.Response(
        ctx,
        response_data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
