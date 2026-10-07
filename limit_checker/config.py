"""Configuration shared by the local checker and the future OCI Function."""

from dataclasses import dataclass
import json
from pathlib import Path
import re


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Monitor:
    name: str
    service_name: str
    limit_name: str
    availability_domain: str | None
    warning_percent: float


@dataclass(frozen=True)
class Config:
    region: str
    home_region: str
    tenancy_id: str
    check_schedule_utc: str
    email_recipients: tuple[str, ...]
    monitors: tuple[Monitor, ...]


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or "<" in value or ">" in value:
        raise ConfigError(f"{field} must be a non-empty value, not a placeholder")
    return value.strip()


def parse_config(data: object) -> Config:
    if not isinstance(data, dict):
        raise ConfigError("configuration must be a JSON object")

    region = _text(data.get("region"), "region")
    home_region = _text(data.get("home_region"), "home_region")
    tenancy_id = _text(data.get("tenancy_id"), "tenancy_id")
    if not tenancy_id.startswith("ocid1.tenancy."):
        raise ConfigError("tenancy_id must be an OCI tenancy OCID")

    schedule = _text(data.get("check_schedule_utc"), "check_schedule_utc")
    if len(schedule.split()) != 5:
        raise ConfigError("check_schedule_utc must be a five-field UTC cron expression")

    recipients = data.get("email_recipients")
    if not isinstance(recipients, list) or not recipients:
        raise ConfigError("email_recipients must be a non-empty list")
    emails = tuple(_text(item, "email_recipients item") for item in recipients)
    if any("@" not in email for email in emails):
        raise ConfigError("email_recipients contains an invalid address")

    raw_monitors = data.get("monitors")
    if not isinstance(raw_monitors, dict) or not raw_monitors:
        raise ConfigError("monitors must be a non-empty object")
    monitors = []
    for name, item in raw_monitors.items():
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", name):
            raise ConfigError("monitor names must be 1-64 letters, digits, _ or -, starting with a letter")
        if not isinstance(item, dict):
            raise ConfigError(f"monitors.{name} must be an object")
        threshold = item.get("warning_percent")
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not 0 <= threshold < 100:
            raise ConfigError(f"monitors.{name}.warning_percent must be between 0 (inclusive) and 100")
        ad = item.get("availability_domain")
        if item.get("service_name") == "identity" and item.get("limit_name") == "policies-count" and ad is not None:
            raise ConfigError(f"monitors.{name}.identity/policies-count must have no availability_domain")
        monitors.append(
            Monitor(
                name=name,
                service_name=_text(item.get("service_name"), f"monitors.{name}.service_name"),
                limit_name=_text(item.get("limit_name"), f"monitors.{name}.limit_name"),
                availability_domain=None if ad is None else _text(ad, f"monitors.{name}.availability_domain"),
                warning_percent=float(threshold),
            )
        )
    return Config(region, home_region, tenancy_id, schedule, emails, tuple(monitors))


def load_config(path: str | Path) -> Config:
    try:
        return parse_config(json.loads(Path(path).read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot read configuration: {exc}") from exc
