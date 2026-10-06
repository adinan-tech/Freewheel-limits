"""OCI Functions entry point for a scheduled, read-only limit check."""

import json
import os

from limit_checker.checker import check_all
from limit_checker.config import parse_config
from limit_checker.oci_gateway import OciLimitsGateway


def run_check(config_json: str, gateway=None) -> dict:
    config = parse_config(json.loads(config_json))
    if gateway is None:
        gateway = OciLimitsGateway.create(config.region, "resource-principal", None, "DEFAULT")
    results = check_all(config, gateway)
    return {"results": [result.to_dict() for result in results]}


def handler(ctx, data=None):
    from fdk import response

    config_json = os.environ["LIMIT_CHECKER_CONFIG"]
    payload = run_check(config_json)
    print(json.dumps(payload), flush=True)
    if any(result["status"] == "ERROR" for result in payload["results"]):
        raise RuntimeError("one or more configured limits could not be checked")
    return response.Response(
        ctx,
        response_data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
