"""Run configuration preflight or a local read-only limit check."""

import argparse
import json
import sys

from .checker import CheckError, check_all
from .config import ConfigError, load_config
from .oci_gateway import OciLimitsGateway


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Read OCI hard limits and check soft warning thresholds")
    parser.add_argument("command", choices=("preflight", "check"))
    parser.add_argument("--config", required=True, help="JSON configuration file")
    parser.add_argument("--auth", choices=("config", "resource-principal"), default="config")
    parser.add_argument("--oci-config", help="OCI SDK config file; default is ~/.oci/config")
    parser.add_argument("--profile", default="DEFAULT", help="OCI SDK config profile")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        gateway = OciLimitsGateway.create(config.region, args.auth, args.oci_config, args.profile, config.home_region)
        results = check_all(config, gateway)
    except (ConfigError, CheckError, OSError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}), file=sys.stderr)
        return 2

    print(json.dumps({"mode": args.command, "results": [item.to_dict() for item in results]}))
    return 1 if any(item.status == "ERROR" for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
