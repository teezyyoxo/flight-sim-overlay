from __future__ import annotations

import argparse
import os
import threading
import webbrowser

from werkzeug.serving import make_server

from flight_overlay import create_app
from flight_overlay.config import load_dotenv
from flight_overlay.tray import TrayController
from flight_overlay.version import __version__


class ServerThread(threading.Thread):
    def __init__(self, app, host: str, port: int) -> None:
        super().__init__(name="overlay-web", daemon=True)
        self.server = make_server(host, port, app, threaded=True)

    def run(self) -> None:
        self.server.serve_forever()

    def stop(self) -> None:
        self.server.shutdown()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Flight Sim Overlay")
    parser.add_argument("--host", help="Web server bind address")
    parser.add_argument("--port", type=int, help="Web server port")
    parser.add_argument("--no-tray", action="store_true", help="Run without a tray icon")
    parser.add_argument("--demo", action="store_true", help="Use animated demo telemetry")
    parser.add_argument(
        "--open-settings", action="store_true", help="Open settings after startup"
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    host = args.host or os.getenv("FSO_HOST", "127.0.0.1")
    port = args.port or int(os.getenv("FSO_PORT", "5000"))
    if args.demo:
        os.environ["FSO_DEMO_MODE"] = "1"
    app = create_app()
    settings = app.extensions["overlay_settings"]

    server = ServerThread(app, host, port)
    server.start()
    browser_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    base_url = f"http://{browser_host}:{port}"
    print(f"Flight Sim Overlay v{__version__} running at {base_url}/overlay")
    print(f"Settings: {base_url}/settings")
    if args.open_settings:
        webbrowser.open(f"{base_url}/settings")

    def shutdown() -> None:
        server.stop()
        app.extensions["overlay_telemetry"].stop()
        app.extensions["overlay_integrations"].stop()

    if args.no_tray:
        try:
            server.join()
        except KeyboardInterrupt:
            shutdown()
        return
    try:
        tray = TrayController(
            base_url,
            settings,
            app.extensions["overlay_telemetry"],
            app.extensions["overlay_integrations"],
            shutdown,
        )
        tray.run()
    except ImportError:
        print("Tray dependencies unavailable; continuing without the tray icon.")
        try:
            server.join()
        except KeyboardInterrupt:
            shutdown()


if __name__ == "__main__":
    main()
