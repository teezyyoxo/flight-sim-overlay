from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import SettingsStore


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_json(url: str, timeout: float = 6.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "FlightSimOverlay/2.0 (+local companion app)"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object")
    return payload


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coordinate(source: dict[str, Any]) -> dict[str, float] | None:
    lat = _number(source.get("pos_lat", source.get("latitude")))
    lon = _number(source.get("pos_long", source.get("longitude")))
    if lat is None or lon is None:
        return None
    return {"lat": lat, "lon": lon}


class IntegrationManager:
    def __init__(self, settings: SettingsStore) -> None:
        self.settings = settings
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._refresh_simbrief = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_poll = {"simbrief": 0.0, "vatsim": 0.0, "sayintentions": 0.0}
        self._data: dict[str, Any] = {
            "simbrief": self._status("not_configured", "Add a SimBrief user ID"),
            "vatsim": self._status("idle", "Not connected"),
            "sayintentions": self._status("disconnected", "Client not detected"),
        }
        self._plan: dict[str, Any] | None = None

    @staticmethod
    def _status(state: str, label: str, **extra: Any) -> dict[str, Any]:
        return {
            "state": state,
            "label": label,
            "updatedAt": _utc_now(),
            **extra,
        }

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="overlay-integrations", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._data))

    def plan(self) -> dict[str, Any] | None:
        with self._lock:
            return json.loads(json.dumps(self._plan)) if self._plan else None

    def request_simbrief_refresh(self) -> None:
        self._refresh_simbrief.set()

    def _set(self, name: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self._data[name] = payload

    def _run(self) -> None:
        while not self._stop.is_set():
            now = time.monotonic()
            settings = self.settings.get()["integrations"]
            force = self._refresh_simbrief.is_set()
            if force:
                self._refresh_simbrief.clear()
            if settings["simbriefEnabled"] and (
                force or now - self._last_poll["simbrief"] >= 300
            ):
                self._poll_simbrief(settings)
                self._last_poll["simbrief"] = now
            elif not settings["simbriefEnabled"]:
                self._set("simbrief", self._status("disabled", "Disabled"))

            if settings["sayintentionsEnabled"] and (
                now - self._last_poll["sayintentions"] >= 5
            ):
                self._poll_sayintentions()
                self._last_poll["sayintentions"] = now
            elif not settings["sayintentionsEnabled"]:
                self._set("sayintentions", self._status("disabled", "Disabled"))

            if settings["vatsimEnabled"] and now - self._last_poll["vatsim"] >= 60:
                self._poll_vatsim(settings)
                self._last_poll["vatsim"] = now
            elif not settings["vatsimEnabled"]:
                self._set("vatsim", self._status("disabled", "Disabled"))
            self._stop.wait(1)

    def _poll_simbrief(self, settings: dict[str, Any]) -> None:
        user = (
            settings.get("simbriefUserId")
            or os.getenv("SIMBRIEF_USER_ID", "")
            or os.getenv("SIMBRIEF_USERNAME", "")
        ).strip()
        if not user:
            self._set(
                "simbrief",
                self._status("not_configured", "Add a SimBrief user ID"),
            )
            return
        query_key = "userid" if user.isdigit() else "username"
        base_url = os.getenv(
            "SIMBRIEF_API_URL", "https://www.simbrief.com/api/xml.fetcher.php"
        )
        url = f"{base_url}?{urllib.parse.urlencode({query_key: user, 'json': 1})}"
        self._set("simbrief", self._status("connecting", "Importing flight plan"))
        try:
            raw = _fetch_json(url, timeout=10)
            plan = self._parse_simbrief(raw)
            with self._lock:
                self._plan = plan
            route_label = " → ".join(
                value for value in (plan.get("origin"), plan.get("destination")) if value
            )
            self._set(
                "simbrief",
                self._status(
                    "connected",
                    route_label or "Flight plan imported",
                    flightPlan={
                        key: value
                        for key, value in plan.items()
                        if key not in {"routePoints"}
                    },
                ),
            )
        except (OSError, ValueError, urllib.error.URLError) as error:
            self._set(
                "simbrief",
                self._status("error", "Import failed", error=str(error)[:180]),
            )

    @staticmethod
    def _parse_simbrief(raw: dict[str, Any]) -> dict[str, Any]:
        general = raw.get("general") or {}
        origin = raw.get("origin") or {}
        destination = raw.get("destination") or {}
        times = raw.get("times") or {}
        params = raw.get("params") or {}
        aircraft = raw.get("aircraft") or {}
        points: list[dict[str, float]] = []
        first = _coordinate(origin)
        if first:
            points.append(first)
        navlog = raw.get("navlog") or {}
        fixes = navlog.get("fix") or []
        if isinstance(fixes, dict):
            fixes = [fixes]
        for fix in fixes if isinstance(fixes, list) else []:
            point = _coordinate(fix if isinstance(fix, dict) else {})
            if point:
                points.append(point)
        last = _coordinate(destination)
        if last:
            points.append(last)
        plan_id = (
            params.get("request_id")
            or general.get("release")
            or f"{origin.get('icao_code', '')}-{destination.get('icao_code', '')}"
        )
        cruise_altitude = _number(
            general.get("initial_altitude", general.get("cruise_altitude"))
        )
        return {
            "id": str(plan_id),
            "origin": str(origin.get("icao_code") or ""),
            "destination": str(destination.get("icao_code") or ""),
            "originName": str(origin.get("name") or ""),
            "destinationName": str(destination.get("name") or ""),
            "callsign": str(
                general.get("icao_airline", "")
                + str(general.get("flight_number", ""))
            ).strip(),
            "aircraft": str(
                aircraft.get("icaocode") or aircraft.get("name") or ""
            ),
            "route": str(general.get("route") or ""),
            "distanceNm": _number(general.get("route_distance")),
            "cruiseAltitudeFt": cruise_altitude,
            "estimatedEnrouteSeconds": _number(times.get("est_time_enroute")),
            "scheduledOut": times.get("sched_out"),
            "scheduledIn": times.get("sched_in"),
            "routePoints": points,
        }

    def _poll_sayintentions(self) -> None:
        url = os.getenv(
            "SAYINTENTIONS_FLIGHT_URL", "http://127.0.0.1:63287/flightJSON"
        )
        raw: dict[str, Any] = {}
        error: Exception | None = None
        try:
            raw = _fetch_json(url, timeout=2)
        except (OSError, ValueError, urllib.error.URLError) as caught:
            error = caught
            local_app_data = os.getenv("LOCALAPPDATA", "")
            file_path = os.getenv("SAYINTENTIONS_FLIGHT_JSON", "").strip()
            if not file_path and local_app_data:
                file_path = str(Path(local_app_data) / "SayIntentionsAI" / "flight.json")
            if file_path:
                try:
                    loaded = json.loads(Path(file_path).read_text(encoding="utf-8"))
                    raw = loaded if isinstance(loaded, dict) else {}
                    error = None
                except (OSError, ValueError) as caught_file:
                    error = caught_file
        details = raw.get("flight_details") if isinstance(raw, dict) else None
        if not isinstance(details, dict) or not details:
            self._set(
                "sayintentions",
                self._status(
                    "disconnected",
                    "Client not detected",
                    error=str(error)[:180] if error else None,
                ),
            )
            return
        current = details.get("current_flight") or {}
        origin = str(current.get("flight_origin") or "")
        destination = str(current.get("flight_destination") or "")
        label = str(details.get("callsign_icao") or details.get("callsign") or "Connected")
        self._set(
            "sayintentions",
            self._status(
                "connected",
                label,
                flight={
                    "callsign": label,
                    "origin": origin,
                    "destination": destination,
                    "airport": details.get("current_airport"),
                    "runway": details.get("runway"),
                    "clearedForTakeoff": bool(details.get("cleared_for_takeoff")),
                    "assignedGate": current.get("assigned_gate"),
                },
                apiKeyDiscovered=bool(
                    details.get("api_key") or os.getenv("SAYINTENTIONS_API_KEY")
                ),
            ),
        )

    def _poll_vatsim(self, settings: dict[str, Any]) -> None:
        callsign = (
            settings.get("vatsimCallsign")
            or ((self.plan() or {}).get("callsign"))
            or ""
        ).strip().upper()
        if not callsign:
            self._set("vatsim", self._status("idle", "Add a callsign"))
            return
        url = os.getenv(
            "VATSIM_DATA_URL", "https://data.vatsim.net/v3/vatsim-data.json"
        )
        try:
            raw = _fetch_json(url, timeout=8)
            pilot = next(
                (
                    entry
                    for entry in raw.get("pilots", [])
                    if str(entry.get("callsign", "")).upper() == callsign
                ),
                None,
            )
            if pilot:
                plan = pilot.get("flight_plan") or {}
                self._set(
                    "vatsim",
                    self._status(
                        "connected",
                        callsign,
                        pilot={
                            "callsign": callsign,
                            "altitude": pilot.get("altitude"),
                            "groundspeed": pilot.get("groundspeed"),
                            "origin": plan.get("departure"),
                            "destination": plan.get("arrival"),
                        },
                    ),
                )
            else:
                self._set(
                    "vatsim",
                    self._status("online", f"{callsign} not on network"),
                )
        except (OSError, ValueError, urllib.error.URLError) as error:
            self._set(
                "vatsim",
                self._status("error", "Feed unavailable", error=str(error)[:180]),
            )
