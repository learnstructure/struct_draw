"""struct_draw.elements.slab — Plan + section views for slabs.

A slab plan view shows the rectangular slab outline with two
layers of rebar dots (top and bottom) and an isometric section
marker.

A slab section view shows a thin slab strip with both layers of
rebar visible as dots and the cover annotated.
"""

from __future__ import annotations

from typing import Any

from struct_draw.core.composite import (
    draw_concrete_outline,
    draw_dimension,
    draw_line,
    draw_rebar_circle,
    draw_text,
)
from struct_draw.core.data import SlabData
from struct_draw.core.primitives import draw_rectangle


def plan_view(
    target: Any,
    slab: SlabData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
) -> dict[str, Any]:
    """Draw a slab plan view."""
    ox, oy = origin
    L = slab.length_in
    W = slab.width_in
    cover = slab.cover_in

    refs: dict[str, Any] = {"origin": (ox, oy)}

    # Slab outline.
    draw_rectangle(target, origin=(ox, oy), width=L, height=W, layer="CONC_OUTLINE")

    # Bottom-mat rebar dots along x (one row near the bottom, one near the top).
    spacing_x = 6.0
    spacing_y = 6.0
    x = ox + cover
    while x <= ox + L - cover:
        draw_rebar_circle(target, (x, oy + cover), diameter=0.20, layer="REBAR")
        draw_rebar_circle(target, (x, oy + W - cover), diameter=0.20, layer="REBAR")
        x += spacing_x
    y = oy + cover
    while y <= oy + W - cover:
        draw_rebar_circle(target, (ox + cover, y), diameter=0.20, layer="REBAR")
        draw_rebar_circle(target, (ox + L - cover, y), diameter=0.20, layer="REBAR")
        y += spacing_y

    # Length / width dimensions.
    draw_dimension(target, (ox, oy), (ox + L, oy),
                    location=(ox + L / 2.0, oy - 2.0),
                    text_override=f"{L:.0f}\"", layer="DIM_LINEAR")
    draw_dimension(target, (ox, oy), (ox, oy + W),
                    location=(ox - 2.0, oy + W / 2.0),
                    text_override=f"{W:.0f}\"", layer="DIM_LINEAR")

    if title is None:
        title = f"Slab Plan — {slab.name}"
    draw_text(target, title, position=(ox, oy + W + 4.0), height=0.30, layer="TEXT")

    refs.update({"plan_origin": (ox, oy)})
    return refs


def section_view(
    target: Any,
    slab: SlabData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
) -> dict[str, Any]:
    """Draw a slab cross-section (a thin strip)."""
    ox, oy = origin
    L = slab.length_in
    t = slab.thickness_in
    cover = slab.cover_in

    refs: dict[str, Any] = {"origin": (ox, oy)}

    draw_concrete_outline(target, origin=(ox, oy), width=L, height=t, layer="CONC_OUTLINE")

    # Top + bottom rebar dots.
    y_bot = oy + cover
    y_top = oy + t - cover
    spacing = 6.0
    x = ox + cover
    while x <= ox + L - cover:
        draw_rebar_circle(target, (x, y_bot), diameter=0.20, layer="REBAR")
        draw_rebar_circle(target, (x, y_top), diameter=0.20, layer="REBAR")
        x += spacing

    # Thickness dimension.
    draw_dimension(target, (ox, oy), (ox, oy + t),
                    location=(ox - 2.0, oy + t / 2.0),
                    text_override=f"t = {t:.1f}\"", layer="DIM_LINEAR")

    if title is None:
        title = f"Slab Section — {slab.name}"
    draw_text(target, title, position=(ox, oy + t + 4.0), height=0.30, layer="TEXT")

    refs.update({"section_origin": (ox, oy)})
    return refs


__all__ = ["plan_view", "section_view"]