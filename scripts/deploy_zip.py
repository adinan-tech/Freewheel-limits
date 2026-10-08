"""Package and create/update the code-only OCI Function without Docker or OCIR."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from limit_checker.config import load_config  # noqa: E402


def command(args: list[str]) -> str:
    result = subprocess.run(args, text=True, capture_output=True, check=False)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"command failed: {' '.join(args[:4])}\n{detail}")
    return result.stdout


def update_function_with_retry(cli: list[str], function_id: str, common: list[str]) -> str:
    """Retry an update while OCI finishes a previous Function operation."""
    delays = (0, 5, 10, 20, 40)
    args = cli + ["fn", "function", "update", "archive-function", "--function-id", function_id, "--force"] + common
    for attempt, delay in enumerate(delays):
        if delay:
            print(f"Function is busy; retrying in {delay}s...", flush=True)
            time.sleep(delay)
        try:
            return command(args)
        except RuntimeError as error:
            if "currently being modified" not in str(error) or attempt == len(delays) - 1:
                raise
    raise RuntimeError("Function update retry loop ended unexpectedly")


def package_archive(target: Path, dependencies: Path) -> None:
    """Create Oracle's function/ and python/ archive layout."""
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        for directory in ("function/", "python/"):
            info = ZipInfo(directory, (2020, 1, 1, 0, 0, 0))
            info.external_attr = (0o755 << 16) | 0x10
            archive.writestr(info, b"")

        def add(source: Path, name: str) -> None:
            info = ZipInfo(name, (2020, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, source.read_bytes())

        add(ROOT / "function" / "func.py", "function/func.py")
        for source in sorted((ROOT / "limit_checker").rglob("*.py")):
            add(source, f"function/limit_checker/{source.relative_to(ROOT / 'limit_checker').as_posix()}")
        for source in sorted(dependencies.rglob("*")):
            if source.is_file() and "__pycache__" not in source.parts:
                add(source, f"python/{source.relative_to(dependencies).as_posix()}")


def deploy(config_path: Path, profile: str | None) -> str:
    config = load_config(config_path)
    version = command(["oci", "--version"]).strip()
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match or tuple(map(int, match.groups())) < (3, 94, 0):
        raise RuntimeError(f"OCI CLI 3.94+ is required for code-only Functions (found {version})")
    inputs = json.loads(config_path.read_text(encoding="utf-8"))
    prefix = inputs.get("name_prefix", "limit_warnings")
    if not isinstance(prefix, str) or not prefix or "<" in prefix:
        raise ValueError("name_prefix must be a non-empty name")
    runtime_input = {
        key: inputs[key]
        for key in ("region", "home_region", "tenancy_id", "check_schedule_utc", "email_recipients", "monitors")
    }
    runtime_config = {"LIMIT_CHECKER_CONFIG": json.dumps(runtime_input, separators=(",", ":"))}
    metric_compartment_id = inputs.get("function_compartment_id")
    if not isinstance(metric_compartment_id, str) or not metric_compartment_id.startswith("ocid1.compartment."):
        raise ValueError("function_compartment_id must be an OCI compartment OCID")
    runtime_config["METRIC_COMPARTMENT_ID"] = metric_compartment_id
    if sum(len(k.encode()) + len(v.encode()) for k, v in runtime_config.items()) > 4000:
        raise ValueError("Function configuration exceeds the 4 KB OCI limit")

    def output(name: str) -> str:
        return json.loads(command(["terraform", f"-chdir={ROOT / 'terraform'}", "output", "-json", name]))

    app_id = output("application_id")
    if not isinstance(app_id, str) or not app_id.startswith("ocid1.fnapp."):
        raise RuntimeError("run the first Terraform apply to create the Functions application")
    bucket = output("archive_bucket_name")
    namespace = output("archive_namespace")

    cli = ["oci", "--region", config.region]
    if profile:
        cli += ["--profile", profile]
    name = f"{prefix}_checker"
    raw_functions = command(cli + ["fn", "function", "list", "--application-id", app_id, "--all"])
    functions = json.loads(raw_functions)["data"] if raw_functions.strip() else []
    existing = [item for item in functions if item.get("display-name") == name]
    if len(existing) > 1:
        raise RuntimeError(f"more than one Function is named {name}")

    with TemporaryDirectory(prefix="limit-checker-") as scratch:
        folder = Path(scratch)
        dependencies = folder / "python"
        command([
            sys.executable, "-m", "pip", "install", "-r", str(ROOT / "function" / "requirements.txt"),
            "--target", str(dependencies), "--platform", "manylinux2014_x86_64",
            "--python-version", "3.12", "--implementation", "cp", "--only-binary=:all:",
            "--no-compile", "--disable-pip-version-check",
        ])
        archive = folder / "limit-checker.zip"
        package_archive(archive, dependencies)
        if archive.stat().st_size > 250_000_000:
            raise RuntimeError("ZIP exceeds OCI's 250 MB Object Storage archive limit")
        settings = folder / "config.json"
        settings.write_text(json.dumps(runtime_config), encoding="utf-8")
        object_name = f"{name}.zip"
        command(cli + ["os", "object", "put", "--namespace", namespace, "--bucket-name", bucket,
                       "--name", object_name, "--file", str(archive), "--force"])
        common = ["--config", "file://" + settings.as_posix(), "--bucket-name", bucket,
                  "--namespace", namespace, "--object-name", object_name,
                  "--handler", "func.handler", "--memory-in-mbs", "256",
                  "--timeout-in-seconds", "120", "--detached-mode-timeout-in-seconds", "120",
                  "--wait-for-state", "SUCCEEDED"]
        if existing:
            function_id = existing[0]["id"]
            update_function_with_retry(cli, function_id, common)
        else:
            created = json.loads(command(cli + ["fn", "function", "create", "archive-function",
                                        "object-storage", "fn-update-runtime-config",
                                        "--application-id", app_id, "--display-name", name,
                                        "--functions-runtime-name", "python312.ol9"] + common))
            function_id = created["data"]["id"]

    return function_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True, help="customer Terraform JSON variables")
    parser.add_argument("--profile", help="OCI CLI profile; defaults to DEFAULT")
    arguments = parser.parse_args()
    try:
        print(deploy(arguments.config, arguments.profile))
    except (OSError, ValueError, RuntimeError, KeyError, json.JSONDecodeError) as error:
        parser.exit(1, f"ZIP deployment failed: {error}\n")
