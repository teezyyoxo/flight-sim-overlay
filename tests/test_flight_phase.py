from flight_overlay.config import DEFAULT_SETTINGS
from flight_overlay.flight_phase import FlightPhaseDetector
from flight_overlay.models import Telemetry


CONFIG = DEFAULT_SETTINGS["flightPhases"]


def settle(detector, telemetry, expected, now, progress=0, cruise=30000):
    detector.update(telemetry, CONFIG, progress, cruise, now=now)
    result = detector.update(
        telemetry,
        CONFIG,
        progress,
        cruise,
        now=now + CONFIG["transitionConfirmSeconds"] + 0.1,
    )
    assert result.id == expected
    return now + CONFIG["transitionConfirmSeconds"] + 0.1


def test_gate_to_cruise_transitions_are_confirmed():
    detector = FlightPhaseDetector()
    now = 0.0
    gate = Telemetry(
        ground_speed=0, agl=0, altitude=500, vertical_speed=0,
        on_ground=True, parking_brake=True, engines_running=True,
    )
    assert detector.update(gate, CONFIG, 0, 30000, now=now).id == "at_gate"

    taxi = Telemetry(
        ground_speed=12, agl=0, altitude=500, vertical_speed=0,
        on_ground=True, parking_brake=False, engines_running=True,
    )
    now = settle(detector, taxi, "taxiing_departure", 1, progress=1)

    departure = Telemetry(
        ground_speed=130, agl=120, altitude=620, vertical_speed=1800,
        on_ground=False, parking_brake=False, engines_running=True,
    )
    now = settle(detector, departure, "departure", now + 1, progress=3)

    climb = Telemetry(
        ground_speed=220, agl=1800, altitude=2300, vertical_speed=1800,
        on_ground=False, parking_brake=False, engines_running=True,
    )
    now = settle(detector, climb, "climb", now + 1, progress=10)

    cruise = Telemetry(
        ground_speed=440, agl=29500, altitude=30000, vertical_speed=50,
        on_ground=False, parking_brake=False, engines_running=True,
    )
    settle(detector, cruise, "cruise", now + 1, progress=40)


def test_go_around_returns_approach_to_climb():
    detector = FlightPhaseDetector()
    approach = Telemetry(
        ground_speed=150, agl=1800, altitude=2500, vertical_speed=-700,
        on_ground=False,
    )
    assert detector.update(approach, CONFIG, 85, 30000, now=0).id == "approach"
    go_around = Telemetry(
        ground_speed=170, agl=4500, altitude=5200, vertical_speed=1600,
        on_ground=False,
    )
    settle(detector, go_around, "climb", 1, progress=88)
