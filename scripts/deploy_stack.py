"""Deploy or recreate the full limit-warning stack with one command."""

import argparse
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
TERRAFORM = ROOT / "terraform"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy_zip import deploy  # noqa: E402


def command(args: list[str], *, allow_not_found: bool = False) -> str:
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=900, check=False)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        if allow_not_found and "NotAuthorizedOrNotFound" in detail:
            return ""
        raise RuntimeError(f"command failed: {' '.join(args[:4])}\n{detail}")
    if result.stdout:
        print(result.stdout, end="")
    return result.stdout


def terraform(action: str, config: Path, function_id: str | None = None) -> None:
    args = ["terraform", f"-chdir={TERRAFORM}", action, "-input=false", "-auto-approve", f"-var-file={config}"]
    if function_id:
        args.append(f"-var=function_id={function_id}")
    command(args)


def deployed_function_id(settings: dict[str, object], profile: str | None) -> str | None:
    """Find the named Function from the current Terraform application output."""
    try:
        app_id = json.loads(command(["terraform", f"-chdir={TERRAFORM}", "output", "-json", "application_id"]))
    except (RuntimeError, json.JSONDecodeError):
        return None
    if not isinstance(app_id, str) or not app_id.startswith("ocid1.fnapp."):
        return None
    prefix = settings.get("name_prefix", "limit_warnings")
    if not isinstance(prefix, str):
        raise ValueError("name_prefix must be a string")
    cli = ["oci", "--region", str(settings["region"])]
    if profile:
        cli += ["--profile", profile]
    functions = json.loads(command(cli + ["fn", "function", "list", "--application-id", app_id, "--all"]))["data"]
    matches = [item.get("id") for item in functions if item.get("display-name") == f"{prefix}_checker"]
    if len(matches) > 1:
        raise RuntimeError(f"more than one Function is named {prefix}_checker")
    return matches[0] if matches else None


def destroy(config: Path, profile: str | None) -> None:
    command(["terraform", f"-chdir={TERRAFORM}", "init", "-input=false"])
    settings = json.loads(config.read_text(encoding="utf-8"))
    function_id = deployed_function_id(settings, profile)
    if function_id:
        cli = ["oci", "--region", settings["region"]]
        if profile:
            cli += ["--profile", profile]
        command(cli + ["fn", "function", "delete", "--function-id", function_id, "--force", "--wait-for-state", "SUCCEEDED"], allow_not_found=True)
    terraform("destroy", config, function_id)


def apply(config: Path, profile: str | None) -> None:
    command(["terraform", f"-chdir={TERRAFORM}", "init", "-input=false"])
    settings = json.loads(config.read_text(encoding="utf-8"))
    function_id = deployed_function_id(settings, profile)
    is_new_stack = function_id is None

    # 1. First Terraform apply: create the Application, logs, archive policy, and bucket if needed.
    terraform("apply", config, function_id)

    # 2. Create or update the code-only Function.
    function_id = deploy(config, profile)

    # 3. New Function only: second Terraform apply receives its OCID internally and creates IAM, schedule, topic, and alarms.
    if is_new_stack:
        terraform("apply", config, function_id)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("apply", "destroy", "recreate"))
    parser.add_argument("--config", type=Path, required=True, help="customer Terraform JSON variables")
    parser.add_argument("--profile", help="OCI CLI profile; defaults to DEFAULT")
    args = parser.parse_args()
    config = args.config.resolve()
    if not config.is_file():
        parser.error(f"configuration file not found: {config}")
    try:
        if args.action == "destroy":
            destroy(config, args.profile)
        elif args.action == "recreate":
            destroy(config, args.profile)
            apply(config, args.profile)
        else:
            apply(config, args.profile)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"stack deployment failed: {error}\n")
    return 0


if __name__ == "__main__":
    main()
