"""Compatibility launcher for Flight Sim Overlay's built-in demo telemetry."""

from __future__ import annotations

import os
import sys

from server import main


if __name__ == "__main__":
    os.environ["FSO_DEMO_MODE"] = "1"
    if "--demo" not in sys.argv:
        sys.argv.append("--demo")
    main()
