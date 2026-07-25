from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from typing import Any

from flask import Flask, jsonify, render_template, request

from .config import (
    AIRCRAFT_ICONS,
    ROOT,
    THEMES,
    SettingsStore,
    load_dotenv,
    public_settings_payload,
)
from .flight_phase import FlightPhaseDetector
from .integrations import IntegrationManager
from .route_progress import RouteProgressTracker
from .telemetry import TelemetryService
from .version import __version__


def _format_eta(seconds_since_midnight: float | None) -> str | None:
    if seconds_since_midnight is None:
        return None
    seconds = int(seconds_since_midnight) % 86400
    hours, remainder = divmod(seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}Z"


class OverlayState:
    def __init__(
        self,
        settings: SettingsStore,
        telemetry: TelemetryService,
        integrations: IntegrationManager,
    ) -> None:
        self.settings = settings
        self.telemetry = telemetry
        self.integrations = integrations
        self.phase_detector = FlightPhaseDetector()
        self.progress_tracker = RouteProgressTracker()
        self._lock = threading.RLock()

    def data(self) -> dict[str, Any]:
        with self._lock:
            telemetry, connection = self.telemetry.snapshot()
            settings = self.settings.get()
            plan = self.integrations.plan()
            self.progress_tracker.set_plan(plan)
            route_progress = self.progress_tracker.update(
                telemetry.latitude, telemetry.longitude
            )
            cruise_altitude = (plan or {}).get("cruiseAltitudeFt")
            phase = self.phase_detector.update(
                telemetry,
                settings["flightPhases"],
                route_progress=route_progress,
                cruise_altitude=cruise_altitude,
            )
            telemetry_payload = telemetry.as_dict()
            telemetry_payload["gps_eta_formatted"] = _format_eta(telemetry.gps_eta)
            telemetry_payload["distance_unit"] = "nm"
            return {
                "version": __version__,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "telemetry": telemetry_payload,
                "connection": connection.as_dict(),
                "phase": phase.as_dict(),
                "progress": phase.progress,
                "progressSource": (
                    "simbrief_route" if phase.progress is not None else "unavailable"
                ),
                "flightPlan": (
                    {
                        key: value
                        for key, value in plan.items()
                        if key != "routePoints"
                    }
                    if plan
                    else None
                ),
                "integrations": self.integrations.snapshot(),
            }


def create_app(
    *,
    settings_path=None,
    start_services: bool = True,
) -> Flask:
    load_dotenv()
    app = Flask(
        __name__,
        static_folder=str(ROOT / "static"),
        template_folder=str(ROOT / "templates"),
    )
    app.config["JSON_SORT_KEYS"] = False

    settings = SettingsStore(settings_path)
    telemetry = TelemetryService(settings)
    integrations = IntegrationManager(settings)
    state = OverlayState(settings, telemetry, integrations)

    app.extensions["overlay_settings"] = settings
    app.extensions["overlay_telemetry"] = telemetry
    app.extensions["overlay_integrations"] = integrations
    app.extensions["overlay_state"] = state

    if start_services:
        telemetry.start()
        integrations.start()

    @app.after_request
    def add_headers(response):
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/")
    @app.get("/overlay")
    def overlay():
        return render_template("overlay.html", version=__version__)

    @app.get("/preview")
    def preview():
        return render_template("overlay.html", version=__version__, preview=True)

    @app.get("/settings")
    def settings_page():
        return render_template("settings.html", version=__version__)

    @app.get("/healthz")
    def health():
        _, connection = telemetry.snapshot()
        return jsonify(
            {
                "ok": True,
                "version": __version__,
                "simconnect": connection.as_dict(),
            }
        )

    @app.get("/api/data")
    def data():
        return jsonify(state.data())

    @app.get("/api/settings")
    def get_settings():
        return jsonify(public_settings_payload(settings.get()))

    @app.put("/api/settings")
    def put_settings():
        candidate = request.get_json(silent=True)
        if not isinstance(candidate, dict):
            return jsonify({"error": "Expected a JSON settings object"}), 400
        saved = settings.save(candidate)
        return jsonify(public_settings_payload(saved))

    @app.post("/api/settings/reset")
    def reset_settings():
        return jsonify(public_settings_payload(settings.reset()))

    @app.post("/api/theme/random")
    def random_theme():
        return jsonify(public_settings_payload(settings.random_theme()))

    @app.post("/api/simbrief/refresh")
    def refresh_simbrief():
        integrations.request_simbrief_refresh()
        return jsonify({"ok": True, "message": "SimBrief refresh queued"}), 202

    @app.get("/api/catalog")
    def catalog():
        return jsonify(
            {
                "themes": [{"id": key, **value} for key, value in THEMES.items()],
                "aircraftIcons": [
                    {"id": key, "name": value}
                    for key, value in AIRCRAFT_ICONS.items()
                ],
            }
        )

    return app
