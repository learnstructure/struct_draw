"""Pure 2D geometry helpers.

These functions are intentionally **drawing-side only** — they have
nothing to do with engineering calculations. They are used by
adapters to translate producer coordinates into paper coordinates,
by viewports to compute scaled layouts, and by backends for
trivial geometric tasks.

All functions are pure (no side effects), unit-agnostic (operate on
arbitrary numeric scales), and work on ``(x, y)`` tuples.
"""

from __future__ import annotations

from math import cos, radians, sin
from typing import Iterable, Sequence


Point = tuple[float, float]
BoundingBox = tuple[float, float, float, float]  # (x_min, y_min, x_max, y_max)


def bounding_box(points: Iterable[Point]) -> BoundingBox:
    """Return the axis-aligned bounding box of a sequence of points.

    Empty input returns ``(0, 0, 0, 0)``.
    """
    xs: list[float] = []
    ys: list[float] = []
    for x, y in points:
        xs.append(x)
        ys.append(y)
    if not xs:
        return (0.0, 0.0, 0.0, 0.0)
    return (min(xs), min(ys), max(xs), max(ys))


def translate(point: Point, dx: float, dy: float) -> Point:
    """Translate ``point`` by ``(dx, dy)``."""
    return (point[0] + dx, point[1] + dy)


def scale(point: Point, factor: float, *, origin: Point = (0.0, 0.0)) -> Point:
    """Scale ``point`` by ``factor`` about ``origin``."""
    return (
        origin[0] + (point[0] - origin[0]) * factor,
        origin[1] + (point[1] - origin[1]) * factor,
    )


def rotate(point: Point, angle_deg: float, *, origin: Point = (0.0, 0.0)) -> Point:
    """Rotate ``point`` by ``angle_deg`` degrees about ``origin``."""
    theta = radians(angle_deg)
    cx, cy = origin
    px, py = point
    dx, dy = px - cx, py - cy
    return (
        cx + dx * cos(theta) - dy * sin(theta),
        cy + dx * sin(theta) + dy * cos(theta),
    )


def fits_in(inner: BoundingBox, outer: BoundingBox, *, margin: float = 0.0) -> bool:
    """Check if ``inner`` fits inside ``outer`` with an optional margin."""
    return (
        inner[0] >= outer[0] + margin
        and inner[1] >= outer[1] + margin
        and inner[2] <= outer[2] - margin
        and inner[3] <= outer[3] - margin
    )


def union_box(*boxes: BoundingBox) -> BoundingBox:
    """Return the axis-aligned union of several bounding boxes."""
    if not boxes:
        return (0.0, 0.0, 0.0, 0.0)
    return (
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )


def is_close(a: float, b: float, *, abs_tol: float = 1e-9) -> bool:
    """Floating-point equality with a tolerance."""
    return abs(a - b) <= abs_tol


def polyline_length(points: Sequence[Point]) -> float:
    """Total length of a polyline (sum of segment distances)."""
    total = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        dx = x1 - x0
        dy = y1 - y0
        total += (dx * dx + dy * dy) ** 0.5
    return total