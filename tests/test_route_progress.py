from flight_overlay.route_progress import RouteProgressTracker, haversine_nm


def test_haversine_known_distance():
    assert 59 < haversine_nm((0, 0), (0, 1)) < 61


def test_progress_projects_live_position_onto_route():
    tracker = RouteProgressTracker()
    tracker.set_plan(
        {
            "id": "test-route",
            "distanceNm": 600,
            "routePoints": [
                {"lat": 0, "lon": 0},
                {"lat": 0, "lon": 5},
                {"lat": 0, "lon": 10},
            ],
        }
    )
    assert 49 < tracker.update(0.01, 5) < 51


def test_progress_does_not_move_backward():
    tracker = RouteProgressTracker()
    tracker.set_plan(
        {
            "id": "route",
            "routePoints": [{"lat": 0, "lon": 0}, {"lat": 0, "lon": 10}],
        }
    )
    first = tracker.update(0, 7)
    second = tracker.update(0, 4)
    assert second >= first


def test_new_plan_resets_progress():
    tracker = RouteProgressTracker()
    tracker.set_plan(
        {"id": "one", "routePoints": [{"lat": 0, "lon": 0}, {"lat": 0, "lon": 1}]}
    )
    tracker.update(0, 0.8)
    tracker.set_plan(
        {"id": "two", "routePoints": [{"lat": 1, "lon": 0}, {"lat": 1, "lon": 1}]}
    )
    assert tracker.progress is None
