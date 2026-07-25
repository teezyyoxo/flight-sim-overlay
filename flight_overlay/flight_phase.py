from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from .models import Telemetry


PHASES = [
    {"id": "at_gate", "label": "At the gate", "short": "Gate"},
    {"id": "taxiing_departure", "label": "Taxiing", "short": "Taxi"},
    {"id": "departure", "label": "Departure", "short": "Depart"},
    {"id": "climb", "label": "Climb", "short": "Climb"},
    {"id": "cruise", "label": "Cruise", "short": "Cruise"},
    {"id": "descent", "label": "Descent", "short": "Descend"},
    {"id": "approach", "label": "Approach", "short": "Approach"},
    {"id": "arrival", "label": "Arrival", "short": "Land"},
    {"id": "taxiing_arrival", "label": "Taxiing", "short": "Taxi"},
    {"id": "at_gate_arrival", "label": "At the gate", "short": "Gate"},
]

PHASE_INDEX = {phase["id"]: index for index, phase in enumerate(PHASES)}


@dataclass
class PhaseSnapshot:
    id: str
    label: str
    index: int
    progress: float | None
    changed_at: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "index": self.index,
            "progress": round(self.progress, 1) if self.progress is not None else None,
            "changedAt": self.changed_at,
            "timeline": PHASES,
        }


class FlightPhaseDetector:
    """Stateful flight-phase detection with transition confirmation.

    Sim telemetry is noisy around runway and gate thresholds. A candidate state must
    remain stable for the configured confirmation period before it becomes visible.
    State transitions are directional, so a brief touchdown or altitude wobble cannot
    send the overlay backwards through the flight.
    """

    def __init__(self) -> None:
        self.phase = "at_gate"
        self.changed_at = time.monotonic()
        self._pending: str | None = None
        self._pending_since = 0.0
        self._initialized = False

    def reset(self) -> None:
        self.__init__()

    @staticmethod
    def _number(value: float | None, fallback: float = 0.0) -> float:
        return fallback if value is None else float(value)

    def _initial_phase(
        self, t: Telemetry, route_progress: float | None, cruise_altitude: float | None
    ) -> str:
        gs = self._number(t.ground_speed)
        agl = self._number(t.agl, self._number(t.altitude))
        vs = self._number(t.vertical_speed)
        on_ground = bool(t.on_ground) if t.on_ground is not None else agl < 30
        if on_ground:
            return "taxiing_departure" if gs > 1 else "at_gate"
        if agl < 3000 and vs < -100:
            return "approach"
        if vs < -300:
            return "descent"
        if cruise_altitude and abs(self._number(t.altitude) - cruise_altitude) < 1500:
            return "cruise"
        return "climb" if vs >= -100 else "descent"

    def _candidate(
        self,
        t: Telemetry,
        config: dict[str, Any],
        route_progress: float | None,
        cruise_altitude: float | None,
    ) -> str:
        gs = self._number(t.ground_speed)
        agl = self._number(t.agl, self._number(t.altitude))
        altitude = self._number(t.altitude)
        vs = self._number(t.vertical_speed)
        on_ground = bool(t.on_ground) if t.on_ground is not None else agl < 30
        parked = bool(t.parking_brake)
        engines = True if t.engines_running is None else bool(t.engines_running)

        gate_speed = float(config["gateSpeedKts"])
        takeoff_speed = float(config["takeoffSpeedKts"])
        airborne_agl = float(config["airborneAglFt"])
        approach_agl = float(config["approachAglFt"])
        stable_vs = float(config["verticalSpeedStableFpm"])
        tolerance = float(config["cruiseAltitudeToleranceFt"])

        if self.phase == "at_gate":
            if not on_ground or agl >= airborne_agl:
                return "departure"
            if gs > gate_speed and engines:
                return "taxiing_departure"
        elif self.phase == "taxiing_departure":
            if not on_ground or agl >= airborne_agl or gs >= takeoff_speed:
                return "departure"
            if gs <= gate_speed and parked:
                return "at_gate"
        elif self.phase == "departure":
            if not on_ground and agl >= max(1000, airborne_agl * 3):
                return "climb"
            if on_ground and gs < takeoff_speed * 0.65:
                return "taxiing_departure"
        elif self.phase == "climb":
            if agl <= approach_agl and vs < -stable_vs:
                return "approach"
            if vs < -stable_vs:
                return "descent"
            if (
                cruise_altitude
                and abs(altitude - cruise_altitude) <= tolerance
                and abs(vs) <= stable_vs
            ):
                return "cruise"
        elif self.phase == "cruise":
            if agl <= approach_agl and vs < stable_vs:
                return "approach"
            if vs < -stable_vs or (
                cruise_altitude
                and altitude < cruise_altitude - tolerance
            ):
                return "descent"
        elif self.phase == "descent":
            if on_ground:
                return "arrival"
            if agl <= approach_agl:
                return "approach"
            if (
                cruise_altitude
                and abs(altitude - cruise_altitude) <= tolerance
                and abs(vs) <= stable_vs
            ):
                return "cruise"
        elif self.phase == "approach":
            if on_ground or (agl < airborne_agl * 0.5 and gs > gate_speed):
                return "arrival"
            if agl > approach_agl * 1.35 and vs > stable_vs:
                return "climb"  # go-around
        elif self.phase == "arrival":
            if on_ground and gs < takeoff_speed * 0.7:
                return "taxiing_arrival"
            if not on_ground and agl > airborne_agl * 2:
                return "climb"  # rejected touchdown / go-around
        elif self.phase == "taxiing_arrival":
            if not on_ground:
                return "arrival"
            if gs <= gate_speed and (parked or not engines):
                return "at_gate_arrival"
        elif self.phase == "at_gate_arrival":
            if gs > gate_speed:
                return "taxiing_arrival"
        return self.phase

    def update(
        self,
        telemetry: Telemetry,
        config: dict[str, Any],
        route_progress: float | None = None,
        cruise_altitude: float | None = None,
        now: float | None = None,
    ) -> PhaseSnapshot:
        timestamp = time.monotonic() if now is None else now
        if not self._initialized:
            self.phase = self._initial_phase(
                telemetry, route_progress, cruise_altitude
            )
            self.changed_at = timestamp
            self._initialized = True

        candidate = self._candidate(
            telemetry, config, route_progress, cruise_altitude
        )
        if candidate == self.phase:
            self._pending = None
        elif candidate != self._pending:
            self._pending = candidate
            self._pending_since = timestamp
        elif timestamp - self._pending_since >= float(
            config["transitionConfirmSeconds"]
        ):
            self.phase = candidate
            self.changed_at = timestamp
            self._pending = None

        meta = PHASES[PHASE_INDEX[self.phase]]
        return PhaseSnapshot(
            id=self.phase,
            label=meta["label"],
            index=PHASE_INDEX[self.phase],
            progress=(
                max(0, min(100, route_progress))
                if route_progress is not None
                else None
            ),
            changed_at=self.changed_at,
        )
