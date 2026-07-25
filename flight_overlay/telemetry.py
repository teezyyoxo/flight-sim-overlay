from __future__ import annotations

import math
import os
import random
import threading
import time
from datetime import datetime, timezone
from typing import Any

from .config import SettingsStore
from .models import ConnectionHealth, Telemetry


SIMVARS = {
    "airspeed": "AIRSPEED_INDICATED",
    "ground_speed": "GROUND_VELOCITY",
    "altitude": "PLANE_ALTITUDE",
    "agl": "PLANE_ALT_ABOVE_GROUND",
    "vertical_speed": "VERTICAL_SPEED",
    "heading": "PLANE_HEADING_DEGREES_MAGNETIC",
    "latitude": "PLANE_LATITUDE",
    "longitude": "PLANE_LONGITUDE",
    "distance": "GPS_TARGET_DISTANCE",
    "gps_ete": "GPS_ETE",
    "gps_eta": "GPS_ETA",
    "on_ground": "SIM_ON_GROUND",
    "parking_brake": "BRAKE_PARKING_POSITION",
    "engines_running": "GENERAL_ENG_COMBUSTION:1",
}


class TelemetryService:
    def __init__(self, settings: SettingsStore) -> None:
        self.settings = settings
        self._telemetry = Telemetry()
        self._health = ConnectionHealth()
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._demo_started = time.monotonic()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="overlay-telemetry", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    def snapshot(self) -> tuple[Telemetry, ConnectionHealth]:
        with self._lock:
            return Telemetry(**self._telemetry.as_dict()), ConnectionHealth(
                **self._health.as_dict()
            )

    def _set(self, telemetry: Telemetry, health: ConnectionHealth) -> None:
        with self._lock:
            self._telemetry = telemetry
            self._health = health

    @staticmethod
    def _safe_get(requests: Any, name: str) -> Any:
        try:
            return requests.get(name)
        except Exception:
            return None

    @staticmethod
    def _float(value: Any) -> float | None:
        try:
            number = float(value)
            return number if math.isfinite(number) else None
        except (TypeError, ValueError):
            return None

    def _read_simconnect(self, requests: Any) -> Telemetry:
        values = {
            field: self._safe_get(requests, simvar)
            for field, simvar in SIMVARS.items()
        }
        heading_radians = self._float(values["heading"])
        distance_meters = self._float(values["distance"])
        return Telemetry(
            airspeed=self._float(values["airspeed"]),
            ground_speed=self._float(values["ground_speed"]),
            altitude=self._float(values["altitude"]),
            agl=self._float(values["agl"]),
            vertical_speed=self._float(values["vertical_speed"]),
            heading=(
                math.degrees(heading_radians) % 360
                if heading_radians is not None
                else None
            ),
            latitude=self._float(values["latitude"]),
            longitude=self._float(values["longitude"]),
            distance=(
                distance_meters / 1852 if distance_meters is not None else None
            ),
            gps_ete=self._float(values["gps_ete"]),
            gps_eta=self._float(values["gps_eta"]),
            on_ground=(
                bool(values["on_ground"]) if values["on_ground"] is not None else None
            ),
            parking_brake=(
                bool(values["parking_brake"])
                if values["parking_brake"] is not None
                else None
            ),
            engines_running=(
                bool(values["engines_running"])
                if values["engines_running"] is not None
                else None
            ),
        )

    def _demo(self) -> Telemetry:
        elapsed = (time.monotonic() - self._demo_started) % 180
        # A compressed three-minute flight exercises every phase in the UI.
        if elapsed < 15:
            gs, agl, altitude, vs, on_ground, progress = (
                elapsed * 1.3,
                0,
                620,
                0,
                True,
                elapsed / 15 * 2,
            )
        elif elapsed < 28:
            part = (elapsed - 15) / 13
            gs, agl, altitude, vs, on_ground, progress = (
                20 + part * 130,
                part * 1200,
                620 + part * 1200,
                2200,
                part < 0.2,
                2 + part * 6,
            )
        elif elapsed < 65:
            part = (elapsed - 28) / 37
            gs, agl, altitude, vs, on_ground, progress = (
                180 + part * 250,
                1200 + part * 28800,
                1820 + part * 28800,
                1800,
                False,
                8 + part * 28,
            )
        elif elapsed < 105:
            part = (elapsed - 65) / 40
            gs, agl, altitude, vs, on_ground, progress = (
                440,
                30000,
                30620,
                math.sin(part * math.pi * 3) * 80,
                False,
                36 + part * 30,
            )
        elif elapsed < 145:
            part = (elapsed - 105) / 40
            gs, agl, altitude, vs, on_ground, progress = (
                420 - part * 260,
                30000 - part * 28500,
                30620 - part * 28500,
                -1900,
                False,
                66 + part * 28,
            )
        elif elapsed < 155:
            part = (elapsed - 145) / 10
            gs, agl, altitude, vs, on_ground, progress = (
                160 - part * 80,
                max(0, 1500 - part * 1500),
                620 + max(0, 1500 - part * 1500),
                -700,
                part > 0.92,
                94 + part * 3,
            )
        else:
            part = (elapsed - 155) / 25
            gs, agl, altitude, vs, on_ground, progress = (
                max(0, 75 * (1 - part)),
                0,
                620,
                0,
                True,
                97 + part * 3,
            )
        return Telemetry(
            airspeed=max(0, gs + random.uniform(-2, 2)),
            ground_speed=max(0, gs),
            altitude=altitude,
            agl=agl,
            vertical_speed=vs,
            heading=(82 + elapsed * 0.35) % 360,
            latitude=36.0800 + progress * 0.0067,
            longitude=-115.1522 + progress * 0.0051,
            distance=max(0, (100 - progress) * 2.1),
            gps_ete=max(0, (100 - progress) * 68),
            gps_eta=(datetime.now(timezone.utc).timestamp() + (100 - progress) * 68)
            % 86400,
            on_ground=on_ground,
            parking_brake=on_ground and gs < 1,
            engines_running=True,
        )

    def _run(self) -> None:
        sim = None
        requests = None
        next_retry = 0.0
        while not self._stop.is_set():
            config = self.settings.get()
            poll_seconds = config["telemetry"]["pollIntervalMs"] / 1000
            demo = config["telemetry"]["demoMode"] or os.getenv(
                "FSO_DEMO_MODE", ""
            ).lower() in {"1", "true", "yes", "on"}
            if demo:
                self._set(
                    self._demo(),
                    ConnectionHealth(
                        state="demo",
                        label="Demo telemetry",
                        last_update=datetime.now(timezone.utc).isoformat(),
                        source="demo",
                    ),
                )
                self._stop.wait(poll_seconds)
                continue
            if requests is None and time.monotonic() >= next_retry:
                try:
                    from SimConnect import AircraftRequests, SimConnect

                    sim = SimConnect()
                    requests = AircraftRequests(sim, _time=100)
                except Exception as error:
                    next_retry = time.monotonic() + config["telemetry"][
                        "connectionRetrySeconds"
                    ]
                    self._set(
                        Telemetry(),
                        ConnectionHealth(
                            state="disconnected",
                            label="Waiting for SimConnect",
                            error=str(error)[:180],
                        ),
                    )
            if requests is not None:
                try:
                    telemetry = self._read_simconnect(requests)
                    if telemetry.latitude is None and telemetry.altitude is None:
                        raise RuntimeError("SimConnect returned no telemetry")
                    self._set(
                        telemetry,
                        ConnectionHealth(
                            state="connected",
                            label="SimConnect",
                            last_update=telemetry.timestamp,
                        ),
                    )
                except Exception as error:
                    try:
                        if sim is not None:
                            sim.exit()
                    except Exception:
                        pass
                    sim = None
                    requests = None
                    next_retry = time.monotonic() + config["telemetry"][
                        "connectionRetrySeconds"
                    ]
                    self._set(
                        Telemetry(),
                        ConnectionHealth(
                            state="error",
                            label="SimConnect interrupted",
                            error=str(error)[:180],
                        ),
                    )
            self._stop.wait(poll_seconds)
        try:
            if sim is not None:
                sim.exit()
        except Exception:
            pass
