from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Telemetry:
    airspeed: float | None = None
    ground_speed: float | None = None
    altitude: float | None = None
    agl: float | None = None
    vertical_speed: float | None = None
    heading: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    distance: float | None = None
    gps_ete: float | None = None
    gps_eta: float | None = None
    on_ground: bool | None = None
    parking_brake: bool | None = None
    engines_running: bool | None = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ConnectionHealth:
    state: str = "disconnected"
    label: str = "Waiting for simulator"
    last_update: str | None = None
    error: str | None = None
    source: str = "simconnect"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
