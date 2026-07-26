from flight_overlay.integrations import IntegrationManager


def test_simbrief_parser_builds_route_without_exposing_raw_payload():
    plan = IntegrationManager._parse_simbrief(
        {
            "params": {"request_id": "42"},
            "general": {
                "route_distance": "510",
                "initial_altitude": "35000",
                "icao_airline": "UAL",
                "flight_number": "825",
                "route": "DCT TEST",
            },
            "aircraft": {"icaocode": "B738"},
            "origin": {
                "icao_code": "KDEN", "name": "Denver",
                "pos_lat": "39.86", "pos_long": "-104.67",
            },
            "destination": {
                "icao_code": "KLAS", "name": "Las Vegas",
                "pos_lat": "36.08", "pos_long": "-115.15",
            },
            "navlog": {"fix": [{"pos_lat": "38", "pos_long": "-110"}]},
            "times": {"est_time_enroute": "6000"},
        }
    )
    assert plan["id"] == "42"
    assert plan["callsign"] == "UAL825"
    assert plan["cruiseAltitudeFt"] == 35000
    assert len(plan["routePoints"]) == 3


def test_simbrief_parser_accepts_missing_callsign_parts():
    plan = IntegrationManager._parse_simbrief(
        {
            "params": {"request_id": "43"},
            "general": {"icao_airline": None, "flight_number": None},
            "aircraft": {},
            "origin": {},
            "destination": {},
            "navlog": {},
            "times": {},
        }
    )
    assert plan["callsign"] == ""
