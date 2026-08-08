"""struct_draw.elements.staircase — Plan + section views for staircases.

A staircase plan shows the outline of the stairwell, the two
flights (one going up, one going down), and the landing strip.

A staircase section shows the side elevation of one flight with
treads / risers, the waist slab, and the landing slab.
"""

from __future__ import annotations

import math
from typing import Any

from struct_draw.core.composite import draw_dimension, draw_line, draw_polyline, draw_text
from struct_draw.core.data import StaircaseData
from struct_draw.core.primitives import draw_rectangle


def plan_view(
    target: Any,
    stair: StaircaseData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
) -> dict[str, Any]:
    """Draw a staircase plan view.

    The plan shows the stairwell outline (a rectangle of width
    ``flight_width_in`` and length ``2 * flight_length_in + landing_depth``)
    with the two flights drawn as parallel rectangles inside.
    """
    ox, oy = origin
    W = stair.flight_width_in
    L = stair.flight_length_in
    landing_depth = max(36.0, stair.tread_depth_in * 3.0)
    total_L = 2 * L + landing_depth

    refs: dict[str, Any] = {"origin": (ox, oy)}

    # Stairwell outline.
    draw_rectangle(target, origin=(ox, oy), width=total_L, height=W,
                    layer="CONC_OUTLINE")

    # Flight 1 (bottom half).
    draw_rectangle(target, origin=(ox, oy), width=L, height=W / 2.0 - 1.0,
                    layer="CONC_OUTLINE")
    # Landing strip.
    draw_rectangle(target, origin=(ox + L, oy), width=landing_depth,
                    height=W, layer="CONC_OUTLINE")
    # Flight 2 (top half).
    draw_rectangle(target, origin=(ox + L + landing_depth, oy + W / 2.0 + 1.0),
                    width=L, height=W / 2.0 - 1.0, layer="CONC_OUTLINE")

    # Direction arrows for the two flights.
    draw_line(target, (ox + L * 0.2, oy + W / 4.0),
              (ox + L * 0.8, oy + W / 4.0), layer="REBAR")
    draw_line(target, (ox + L + landing_depth + L * 0.2, oy + 3 * W / 4.0),
              (ox + L + landing_depth + L * 0.8, oy + 3 * W / 4.0),
              layer="REBAR")

    if title is None:
        title = f"Stair Plan — {stair.name}"
    draw_text(target, title, position=(ox, oy + W + 4.0), height=0.30,
              layer="TEXT")

    refs.update({"plan_origin": (ox, oy)})
    return refs


def section_view(
    target: Any,
    stair: StaircaseData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
) -> dict[str, Any]:
    """Draw a staircase section (side elevation of one flight)."""
    ox, oy = origin
    L = stair.flight_length_in
    R = stair.riser_height_in
    T = stair.tread_depth_in
    N = max(1, int(round(L / T)))
    actual_T = L / N
    H = N * R
    slab = stair.slab_thickness_in

    refs: dict[str, Any] = {"origin": (ox, oy)}

    # Waist slab outline (sloped top, flat bottom).
    pts = [
        (ox, oy),
        (ox + L, oy + H),
        (ox + L, oy + H - slab),
        (ox, oy - slab),
        (ox, oy),
    ]
    draw_polyline(target, pts, close=True, layer="CONC_OUTLINE")

    # Treads / risers: a zigzag along the sloped top.
    tread_pts: list[tuple[float, float]] = []
    for i in range(N + 1):
        x_local = i * actual_T
        y_local = i * R
        tread_pts.append((ox + x_local, oy + y_local))
        if i < N:
            tread_pts.append((ox + x_local, oy + y_local - R))
    draw_polyline(target, tread_pts, close=False, layer="CONC_OUTLINE")

    # Floor / landing lines at start and end.
    draw_line(target, (ox - 6.0, oy - slab), (ox + 6.0, oy - slab), layer="CONC_OUTLINE")
    draw_line(target, (ox + L - 6.0, oy + H), (ox + L + 6.0, oy + H), layer="CONC_OUTLINE")

    # Dimensions.
    draw_dimension(target, (ox, oy - slab), (ox + L, oy + H),
                    location=(ox + L / 2.0, oy + H + 4.0),
                    text_override=f"{N} Rises @ {R:.1f}\"",
                    layer="DIM_LINEAR")

    if title is None:
        title = f"Stair Section — {stair.name}"
    draw_text(target, title, position=(ox, oy + H + 12.0), height=0.30,
              layer="TEXT")

    refs.update({"section_origin": (ox, oy)})
    return refs


__all__ = ["plan_view", "section_view"]