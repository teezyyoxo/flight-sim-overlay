from __future__ import annotations

import copy
import json
import os
import random
import threading
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent


THEMES: dict[str, dict[str, str]] = {
    "midnight": {
        "name": "Midnight",
        "description": "The original cyan and orange, carefully refined.",
        "panel": "#101820",
        "panelAlt": "#17232d",
        "text": "#f4f8fb",
        "muted": "#91a5b5",
        "accent": "#00e5ff",
        "accentAlt": "#ff8a3d",
        "good": "#54e39e",
        "warning": "#ffc857",
    },
    "aurora": {
        "name": "Aurora",
        "description": "Arctic teal with a violet horizon.",
        "panel": "#09171c",
        "panelAlt": "#10262d",
        "text": "#eefcff",
        "muted": "#91b9be",
        "accent": "#52f5c8",
        "accentAlt": "#a988ff",
        "good": "#65f2a8",
        "warning": "#ffd166",
    },
    "sunset": {
        "name": "Sunset",
        "description": "Warm coral, amber, and deep plum.",
        "panel": "#23131f",
        "panelAlt": "#351b2b",
        "text": "#fff7f2",
        "muted": "#cfabb8",
        "accent": "#ff7a66",
        "accentAlt": "#ffc857",
        "good": "#8ee3b6",
        "warning": "#ffd166",
    },
    "oceanic": {
        "name": "Oceanic",
        "description": "Atlantic blue with sea-glass highlights.",
        "panel": "#071723",
        "panelAlt": "#0d2938",
        "text": "#effaff",
        "muted": "#8fb4c8",
        "accent": "#37bfff",
        "accentAlt": "#57e0c2",
        "good": "#65e6a7",
        "warning": "#ffd36a",
    },
    "terminal": {
        "name": "Terminal",
        "description": "A crisp green monochrome instrument panel.",
        "panel": "#07130d",
        "panelAlt": "#102218",
        "text": "#dcffe9",
        "muted": "#7faf8e",
        "accent": "#54f58b",
        "accentAlt": "#b8ff65",
        "good": "#54f58b",
        "warning": "#e8dc68",
    },
    "vintage": {
        "name": "Vintage",
        "description": "Cream instruments and aged brass.",
        "panel": "#211c17",
        "panelAlt": "#332b22",
        "text": "#fff5dc",
        "muted": "#c0ad89",
        "accent": "#e7bf6a",
        "accentAlt": "#db805f",
        "good": "#9fca85",
        "warning": "#e7bf6a",
    },
    "lavender": {
        "name": "Lavender",
        "description": "Soft violet with cool blue accents.",
        "panel": "#161424",
        "panelAlt": "#24213a",
        "text": "#f8f5ff",
        "muted": "#aaa5c7",
        "accent": "#b79cff",
        "accentAlt": "#78d5ff",
        "good": "#73e1ad",
        "warning": "#ffd078",
    },
    "ember": {
        "name": "Ember",
        "description": "Charcoal avionics with a bright ember glow.",
        "panel": "#181311",
        "panelAlt": "#2a1d18",
        "text": "#fff6ef",
        "muted": "#c1a397",
        "accent": "#ff5c35",
        "accentAlt": "#ffb347",
        "good": "#74d99f",
        "warning": "#ffcf5c",
    },
    "arctic": {
        "name": "Arctic",
        "description": "A clean, bright flight-deck treatment.",
        "panel": "#eaf3f7",
        "panelAlt": "#d8e7ed",
        "text": "#112936",
        "muted": "#55717e",
        "accent": "#007fa8",
        "accentAlt": "#e8683a",
        "good": "#12885d",
        "warning": "#b67a00",
    },
    "rose": {
        "name": "Rose",
        "description": "Muted rose with pale champagne details.",
        "panel": "#21151c",
        "panelAlt": "#35212d",
        "text": "#fff5f8",
        "muted": "#c6a1b0",
        "accent": "#ff84ad",
        "accentAlt": "#ffd19a",
        "good": "#83deb0",
        "warning": "#ffd16f",
    },
    "sky": {
        "name": "Sky",
        "description": "Daylight blue and cloud-white readouts.",
        "panel": "#0c1c2c",
        "panelAlt": "#15324a",
        "text": "#f4fbff",
        "muted": "#9fbdd0",
        "accent": "#69c6ff",
        "accentAlt": "#ffffff",
        "good": "#70dfac",
        "warning": "#ffe083",
    },
    "lime": {
        "name": "Lime",
        "description": "Electric lime on a near-black panel.",
        "panel": "#0d120c",
        "panelAlt": "#192117",
        "text": "#f7fff2",
        "muted": "#9cab91",
        "accent": "#b7f34a",
        "accentAlt": "#56d9c1",
        "good": "#7ee788",
        "warning": "#f4da5f",
    },
    "copper": {
        "name": "Copper",
        "description": "Burnished copper and cool instrument blue.",
        "panel": "#1b1715",
        "panelAlt": "#30251f",
        "text": "#fff8f2",
        "muted": "#b9a398",
        "accent": "#d98b5f",
        "accentAlt": "#63c9d5",
        "good": "#88d39d",
        "warning": "#efc568",
    },
    "ultraviolet": {
        "name": "Ultraviolet",
        "description": "Deep indigo with vivid neon detail.",
        "panel": "#100d20",
        "panelAlt": "#201941",
        "text": "#faf7ff",
        "muted": "#a59bc7",
        "accent": "#8f6cff",
        "accentAlt": "#f15bff",
        "good": "#65e2ad",
        "warning": "#ffd166",
    },
    "monochrome": {
        "name": "Monochrome",
        "description": "Restrained grayscale for clean productions.",
        "panel": "#111315",
        "panelAlt": "#202428",
        "text": "#f5f7f8",
        "muted": "#a1a8ad",
        "accent": "#e7ecef",
        "accentAlt": "#aeb8bf",
        "good": "#b9dfc8",
        "warning": "#e5d3a3",
    },
}

AIRCRAFT_ICONS = {
    "airliner": "Airliner",
    "jet": "Business jet",
    "prop": "Propeller",
    "fighter": "Fighter",
    "helicopter": "Helicopter",
    "glider": "Glider",
}

METRIC_IDS = [
    "airspeed",
    "groundSpeed",
    "altitude",
    "verticalSpeed",
    "distance",
    "latitude",
    "longitude",
    "ete",
    "eta",
]

DEFAULT_SETTINGS: dict[str, Any] = {
    "appearance": {
        "theme": "midnight",
        "transparency": 30,
        "scale": 100,
        "width": 96,
        "position": "top",
        "offsetX": 0,
        "offsetY": 20,
        "aircraftIcon": "airliner",
        "motionSmoothing": 72,
        "showStatusRail": True,
        "showCoordinates": True,
    },
    "layout": {
        "primaryMetrics": ["airspeed", "groundSpeed", "altitude", "verticalSpeed"],
        "secondaryMetrics": ["distance", "ete", "eta", "latitude", "longitude"],
        "showHeading": True,
        "showProgress": True,
        "showPhaseTimeline": True,
    },
    "telemetry": {
        "pollIntervalMs": 500,
        "connectionRetrySeconds": 5,
        "demoMode": False,
    },
    "flightPhases": {
        "gateSpeedKts": 1.0,
        "taxiSpeedKts": 35.0,
        "takeoffSpeedKts": 45.0,
        "airborneAglFt": 80.0,
        "approachAglFt": 3000.0,
        "cruiseAltitudeToleranceFt": 1200.0,
        "verticalSpeedStableFpm": 300.0,
        "transitionConfirmSeconds": 3.0,
    },
    "integrations": {
        "simbriefEnabled": True,
        "simbriefUserId": "",
        "vatsimEnabled": True,
        "vatsimCallsign": "",
        "sayintentionsEnabled": True,
    },
}


def _deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in update.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        elif key in merged:
            merged[key] = value
    return merged


def _clamp_number(value: Any, low: float, high: float, fallback: float) -> float:
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return fallback


def validate_settings(candidate: dict[str, Any]) -> dict[str, Any]:
    settings = _deep_merge(DEFAULT_SETTINGS, candidate if isinstance(candidate, dict) else {})
    appearance = settings["appearance"]
    if appearance["theme"] not in THEMES:
        appearance["theme"] = "midnight"
    if appearance["aircraftIcon"] not in AIRCRAFT_ICONS:
        appearance["aircraftIcon"] = "airliner"
    if appearance["position"] not in {"top", "bottom"}:
        appearance["position"] = "top"
    appearance["transparency"] = round(
        _clamp_number(appearance["transparency"], 0, 100, 30)
    )
    appearance["scale"] = round(_clamp_number(appearance["scale"], 60, 150, 100))
    appearance["width"] = round(_clamp_number(appearance["width"], 50, 100, 96))
    appearance["offsetX"] = round(_clamp_number(appearance["offsetX"], -2000, 2000, 0))
    appearance["offsetY"] = round(_clamp_number(appearance["offsetY"], 0, 1000, 20))
    appearance["motionSmoothing"] = round(
        _clamp_number(appearance["motionSmoothing"], 0, 100, 72)
    )
    for boolean_key in ("showStatusRail", "showCoordinates"):
        appearance[boolean_key] = bool(appearance[boolean_key])

    layout = settings["layout"]
    used: set[str] = set()
    for key in ("primaryMetrics", "secondaryMetrics"):
        values = layout.get(key, [])
        clean = []
        for metric in values if isinstance(values, list) else []:
            if metric in METRIC_IDS and metric not in used:
                clean.append(metric)
                used.add(metric)
        layout[key] = clean
    for metric in METRIC_IDS:
        if metric not in used:
            layout["secondaryMetrics"].append(metric)
    for key in ("showHeading", "showProgress", "showPhaseTimeline"):
        layout[key] = bool(layout[key])

    telemetry = settings["telemetry"]
    telemetry["pollIntervalMs"] = round(
        _clamp_number(telemetry["pollIntervalMs"], 250, 5000, 500)
    )
    telemetry["connectionRetrySeconds"] = round(
        _clamp_number(telemetry["connectionRetrySeconds"], 1, 60, 5)
    )
    telemetry["demoMode"] = bool(telemetry["demoMode"])

    phases = settings["flightPhases"]
    limits = {
        "gateSpeedKts": (0, 10, 1),
        "taxiSpeedKts": (10, 50, 35),
        "takeoffSpeedKts": (30, 120, 45),
        "airborneAglFt": (20, 500, 80),
        "approachAglFt": (500, 10000, 3000),
        "cruiseAltitudeToleranceFt": (200, 5000, 1200),
        "verticalSpeedStableFpm": (50, 1000, 300),
        "transitionConfirmSeconds": (0, 15, 3),
    }
    for key, (low, high, fallback) in limits.items():
        phases[key] = _clamp_number(phases[key], low, high, fallback)

    integrations = settings["integrations"]
    for key in ("simbriefEnabled", "vatsimEnabled", "sayintentionsEnabled"):
        integrations[key] = bool(integrations[key])
    for key in ("simbriefUserId", "vatsimCallsign"):
        integrations[key] = str(integrations.get(key, "")).strip()[:64]
    return settings


def load_dotenv(path: Path | None = None) -> None:
    """Load a small, dependency-free subset of .env syntax without overwriting OS values."""
    env_path = path or ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        env_path = os.getenv("FSO_CONFIG_PATH", "").strip()
        self.path = path or (Path(env_path) if env_path else ROOT / "config" / "settings.json")
        self._lock = threading.RLock()
        self._settings = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return copy.deepcopy(DEFAULT_SETTINGS)
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return validate_settings(data)
        except (OSError, json.JSONDecodeError):
            return copy.deepcopy(DEFAULT_SETTINGS)

    def get(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._settings)

    def save(self, candidate: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._settings = validate_settings(candidate)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.path.with_suffix(".tmp")
            temp_path.write_text(
                json.dumps(self._settings, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            temp_path.replace(self.path)
            return copy.deepcopy(self._settings)

    def reset(self) -> dict[str, Any]:
        return self.save(DEFAULT_SETTINGS)

    def random_theme(self) -> dict[str, Any]:
        settings = self.get()
        current = settings["appearance"]["theme"]
        choices = [name for name in THEMES if name != current]
        settings["appearance"]["theme"] = random.choice(choices)
        return self.save(settings)


def public_settings_payload(settings: dict[str, Any]) -> dict[str, Any]:
    theme_id = settings["appearance"]["theme"]
    return {
        "settings": settings,
        "theme": {"id": theme_id, **THEMES[theme_id]},
        "themes": [{"id": key, **value} for key, value in THEMES.items()],
        "aircraftIcons": [
            {"id": key, "name": value} for key, value in AIRCRAFT_ICONS.items()
        ],
        "metricIds": METRIC_IDS,
    }
