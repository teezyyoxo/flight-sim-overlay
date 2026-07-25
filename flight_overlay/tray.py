from __future__ import annotations

import threading
import webbrowser
from typing import Any, Callable

from .config import AIRCRAFT_ICONS, THEMES, SettingsStore
from .integrations import IntegrationManager
from .telemetry import TelemetryService


class TrayController:
    def __init__(
        self,
        base_url: str,
        settings: SettingsStore,
        telemetry: TelemetryService,
        integrations: IntegrationManager,
        on_quit: Callable[[], None],
    ) -> None:
        self.base_url = base_url
        self.settings = settings
        self.telemetry = telemetry
        self.integrations = integrations
        self.on_quit = on_quit
        self.icon: Any = None
        self._monitor_stop = threading.Event()

    @staticmethod
    def _make_image(state: str):
        from PIL import Image, ImageDraw

        image = Image.new("RGBA", (64, 64), (13, 20, 27, 255))
        draw = ImageDraw.Draw(image)
        color = {
            "connected": "#50dfa0",
            "demo": "#63c7ff",
            "error": "#ffbc57",
        }.get(state, "#81909c")
        # A compact top-down aircraft mark with a live connection lamp.
        draw.polygon(
            [(32, 7), (38, 27), (55, 37), (53, 43), (37, 38), (36, 53),
             (44, 58), (42, 61), (32, 57), (22, 61), (20, 58), (28, 53),
             (27, 38), (11, 43), (9, 37), (26, 27)],
            fill="#eef6fa",
        )
        draw.ellipse((46, 4, 61, 19), fill=color, outline="#0d141b", width=2)
        return image

    def _connection_label(self, _item=None) -> str:
        _, health = self.telemetry.snapshot()
        return f"SimConnect: {health.label}"

    def _set_theme(self, theme_id: str):
        def callback(_icon, _item):
            value = self.settings.get()
            value["appearance"]["theme"] = theme_id
            self.settings.save(value)

        return callback

    def _set_aircraft(self, aircraft_id: str):
        def callback(_icon, _item):
            value = self.settings.get()
            value["appearance"]["aircraftIcon"] = aircraft_id
            self.settings.save(value)

        return callback

    def _set_transparency(self, transparency: int):
        def callback(_icon, _item):
            value = self.settings.get()
            value["appearance"]["transparency"] = transparency
            self.settings.save(value)

        return callback

    def _quit(self, icon, _item):
        self._monitor_stop.set()
        icon.stop()
        self.on_quit()

    def _monitor(self) -> None:
        previous = None
        while not self._monitor_stop.wait(2):
            _, health = self.telemetry.snapshot()
            if health.state != previous and self.icon:
                self.icon.icon = self._make_image(health.state)
                self.icon.update_menu()
                previous = health.state

    def run(self) -> None:
        import pystray

        themes = pystray.Menu(
            *[
                pystray.MenuItem(
                    data["name"],
                    self._set_theme(theme_id),
                    checked=lambda _item, value=theme_id: self.settings.get()[
                        "appearance"
                    ]["theme"]
                    == value,
                    radio=True,
                )
                for theme_id, data in THEMES.items()
            ]
        )
        aircraft = pystray.Menu(
            *[
                pystray.MenuItem(
                    label,
                    self._set_aircraft(aircraft_id),
                    checked=lambda _item, value=aircraft_id: self.settings.get()[
                        "appearance"
                    ]["aircraftIcon"]
                    == value,
                    radio=True,
                )
                for aircraft_id, label in AIRCRAFT_ICONS.items()
            ]
        )
        transparency = pystray.Menu(
            *[
                pystray.MenuItem(
                    f"{value}%",
                    self._set_transparency(value),
                    checked=lambda _item, candidate=value: self.settings.get()[
                        "appearance"
                    ]["transparency"]
                    == candidate,
                    radio=True,
                )
                for value in (0, 15, 30, 50, 75)
            ]
        )
        menu = pystray.Menu(
            pystray.MenuItem(
                "Open settings",
                lambda _icon, _item: webbrowser.open(f"{self.base_url}/settings"),
                default=True,
            ),
            pystray.MenuItem(
                "Open overlay",
                lambda _icon, _item: webbrowser.open(f"{self.base_url}/overlay"),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self._connection_label, None, enabled=False),
            pystray.MenuItem("Themes", themes),
            pystray.MenuItem(
                "Random theme",
                lambda _icon, _item: self.settings.random_theme(),
            ),
            pystray.MenuItem("Aircraft icon", aircraft),
            pystray.MenuItem("Transparency", transparency),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Refresh SimBrief",
                lambda _icon, _item: self.integrations.request_simbrief_refresh(),
            ),
            pystray.MenuItem(
                "Reset to defaults…",
                lambda _icon, _item: self.settings.reset(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit Flight Sim Overlay", self._quit),
        )
        _, health = self.telemetry.snapshot()
        self.icon = pystray.Icon(
            "flight-sim-overlay",
            self._make_image(health.state),
            "Flight Sim Overlay",
            menu,
        )
        threading.Thread(
            target=self._monitor, name="tray-status", daemon=True
        ).start()
        self.icon.run()
