from __future__ import annotations

import math
from typing import Any


EARTH_RADIUS_NM = 3440.065


def haversine_nm(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    value = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_NM * math.asin(min(1, math.sqrt(value)))


def _project_fraction(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> tuple[float, float]:
    """Return along-segment fraction and approximate cross-track distance in NM."""
    mean_lat = math.radians((start[0] + end[0] + point[0]) / 3)
    scale = max(0.15, math.cos(mean_lat))
    ax, ay = start[1] * scale, start[0]
    bx, by = end[1] * scale, end[0]
    px, py = point[1] * scale, point[0]
    dx, dy = bx - ax, by - ay
    denom = dx * dx + dy * dy
    fraction = 0.0 if denom == 0 else ((px - ax) * dx + (py - ay) * dy) / denom
    fraction = max(0.0, min(1.0, fraction))
    near_x, near_y = ax + fraction * dx, ay + fraction * dy
    distance_degrees = math.hypot(px - near_x, py - near_y)
    return fraction, distance_degrees * 60


class RouteProgressTracker:
    def __init__(self) -> None:
        self.route_id: str | None = None
        self.points: list[tuple[float, float]] = []
        self.segment_lengths: list[float] = []
        self.total_nm = 0.0
        self.progress: float | None = None

    def set_plan(self, plan: dict[str, Any] | None) -> None:
        route_id = str((plan or {}).get("id") or "")
        if route_id == self.route_id:
            return
        points: list[tuple[float, float]] = []
        for raw in (plan or {}).get("routePoints", []):
            try:
                point = (float(raw["lat"]), float(raw["lon"]))
            except (KeyError, TypeError, ValueError):
                continue
            if not points or haversine_nm(points[-1], point) > 0.1:
                points.append(point)
        self.route_id = route_id
        self.points = points
        self.segment_lengths = [
            haversine_nm(points[index], points[index + 1])
            for index in range(max(0, len(points) - 1))
        ]
        computed_total = sum(self.segment_lengths)
        try:
            planned_total = float((plan or {}).get("distanceNm") or 0)
        except (TypeError, ValueError):
            planned_total = 0
        self.total_nm = planned_total if planned_total > 1 else computed_total
        self.progress = None

    def update(self, latitude: float | None, longitude: float | None) -> float | None:
        if latitude is None or longitude is None or len(self.points) < 2:
            return self.progress
        current = (float(latitude), float(longitude))
        cumulative = 0.0
        candidates: list[tuple[float, float]] = []
        computed_total = sum(self.segment_lengths)
        for index, segment_nm in enumerate(self.segment_lengths):
            fraction, cross_track_nm = _project_fraction(
                current, self.points[index], self.points[index + 1]
            )
            along = cumulative + fraction * segment_nm
            route_fraction = along / computed_total if computed_total else 0
            candidates.append((cross_track_nm, route_fraction * 100))
            cumulative += segment_nm

        # Nearest route segment wins. On looping routes prefer the closest candidate
        # that does not jump implausibly far ahead of the previously displayed value.
        candidates.sort(key=lambda candidate: candidate[0])
        raw = candidates[0][1]
        if self.progress is not None:
            plausible = [
                value
                for distance, value in candidates[:8]
                if value >= self.progress - 3 and value <= self.progress + 25
            ]
            if plausible:
                raw = min(plausible, key=lambda value: abs(value - self.progress))
        remaining = haversine_nm(current, self.points[-1])
        if remaining < 1.5:
            self.progress = 100.0
            return self.progress
        if self.progress is None:
            self.progress = raw
        else:
            # Never move the aircraft backwards because a route leg crosses another.
            self.progress = max(self.progress, self.progress * 0.82 + raw * 0.18)
        self.progress = max(0.0, min(100.0, self.progress))
        return self.progress
