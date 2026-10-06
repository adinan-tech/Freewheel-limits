"""Pure limit evaluation; no OCI credentials or notification side effects."""

from dataclasses import asdict, dataclass
from typing import Protocol

from .config import Config, Monitor


class CheckError(Exception):
    pass


@dataclass(frozen=True)
class Definition:
    name: str
    scope_type: str
    availability_supported: bool


@dataclass(frozen=True)
class LimitValue:
    name: str
    scope_type: str
    availability_domain: str | None
    value: float | None


@dataclass(frozen=True)
class Availability:
    used: float | None
    available: float | None


class LimitsGateway(Protocol):
    def definitions(self, config: Config, monitor: Monitor) -> list[Definition]: ...
    def values(self, config: Config, monitor: Monitor, scope_type: str) -> list[LimitValue]: ...
    def availability(self, config: Config, monitor: Monitor) -> Availability: ...


@dataclass(frozen=True)
class Result:
    monitor: str
    service_name: str
    limit_name: str
    region: str
    availability_domain: str | None
    warning_percent: float
    status: str
    scope_type: str | None = None
    hard_limit: float | None = None
    used: float | None = None
    available: float | None = None
    usage_percent: float | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate(config: Config, monitor: Monitor, gateway: LimitsGateway) -> Result:
    """Resolve the current OCI limit and usage, then compare to the soft threshold."""
    base = dict(
        monitor=monitor.name,
        service_name=monitor.service_name,
        limit_name=monitor.limit_name,
        region=config.region,
        availability_domain=monitor.availability_domain,
        warning_percent=monitor.warning_percent,
    )
    try:
        definitions = [
            item for item in gateway.definitions(config, monitor)
            if item.name == monitor.limit_name
        ]
        if len(definitions) != 1:
            raise CheckError("limit definition was not found or was ambiguous")
        definition = definitions[0]
        scope = definition.scope_type
        if scope not in {"GLOBAL", "REGION", "AD"}:
            raise CheckError(f"unsupported limit scope: {scope}")
        if scope == "AD" and not monitor.availability_domain:
            raise CheckError("availability_domain is required for this AD-scoped limit")
        if scope != "AD" and monitor.availability_domain:
            raise CheckError("availability_domain must be omitted for this limit scope")
        if not definition.availability_supported:
            raise CheckError("OCI does not support resource availability for this limit")

        values = [
            item for item in gateway.values(config, monitor, scope)
            if item.name == monitor.limit_name
            and item.scope_type == scope
            and (scope != "AD" or item.availability_domain == monitor.availability_domain)
        ]
        if len(values) != 1:
            raise CheckError("current hard limit was not found or was ambiguous")
        hard_limit = values[0].value
        if hard_limit is None or hard_limit <= 0:
            raise CheckError("current hard limit is missing or not positive")

        availability = gateway.availability(config, monitor)
        if availability.used is None or availability.available is None:
            raise CheckError("OCI did not return both used and available values")
        if availability.used < 0 or availability.available < 0:
            raise CheckError("OCI returned a negative usage or availability value")
        usage_percent = availability.used / hard_limit * 100
        status = "WARNING" if usage_percent >= monitor.warning_percent else "OK"
        return Result(
            **base,
            status=status,
            scope_type=scope,
            hard_limit=hard_limit,
            used=availability.used,
            available=availability.available,
            usage_percent=round(usage_percent, 4),
        )
    except CheckError as exc:
        return Result(**base, status="ERROR", error=str(exc))


def check_all(config: Config, gateway: LimitsGateway) -> list[Result]:
    return [evaluate(config, monitor, gateway) for monitor in config.monitors]
