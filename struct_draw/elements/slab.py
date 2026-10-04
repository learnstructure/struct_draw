"""struct_draw.elements.slab — Plan and section views for slabs."""

from __future__ import annotations

from typing import Any

from struct_draw.core.composite import (
    draw_concrete_outline,
    draw_dimension,
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
    scale: Any | None = None,
    unit: Any | None = None,
) -> dict[str, Any]:
    """Draw a slab plan view."""
    ox, oy = origin
    L = slab.length_in
    W = slab.width_in
    cover = slab.cover_in

    scale = scale or getattr(slab, "scale", None)
    unit = unit or getattr(slab, "unit", None)
    is_metric = unit.is_metric if unit is not None else slab.is_metric

    from struct_draw.core.units import DrawingScale, DrawingUnit, SCALE_1_50, SCALE_1_4_IN
    from struct_draw.style.annotation_config import DEFAULT_ANNOTATION_CONFIG

    d_unit = unit or (DrawingUnit.MM if is_metric else DrawingUnit.IN)
    d_scale = scale or (SCALE_1_50 if is_metric else SCALE_1_4_IN)

    dim_offset = DEFAULT_ANNOTATION_CONFIG.dim_offset(d_scale, d_unit)
    title_h = DEFAULT_ANNOTATION_CONFIG.title_height(d_scale, d_unit)
    dim_style = "DIM_DETAIL" if is_metric else "Linear"

    refs: dict[str, Any] = {"origin": (ox, oy)}

    # Slab outline.
    draw_rectangle(target, origin=(ox, oy), width=L, height=W, layer="CONC_OUTLINE")

    # Bottom-mat rebar dots along perimeter
    spacing_x = 200.0 if is_metric else 6.0
    spacing_y = 200.0 if is_metric else 6.0
    dot_dia = 12.0 if is_metric else 0.50
    x = ox + cover
    while x <= ox + L - cover:
        draw_rebar_circle(target, (x, oy + cover), diameter=dot_dia, layer="REBAR")
        draw_rebar_circle(target, (x, oy + W - cover), diameter=dot_dia, layer="REBAR")
        x += spacing_x
    y = oy + cover
    while y <= oy + W - cover:
        draw_rebar_circle(target, (ox + cover, y), diameter=dot_dia, layer="REBAR")
        draw_rebar_circle(target, (ox + L - cover, y), diameter=dot_dia, layer="REBAR")
        y += spacing_y

    # Length / width dimensions.
    draw_dimension(
        target,
        (ox, oy),
        (ox + L, oy),
        location=(ox + L / 2.0, oy - dim_offset),
        text_override=d_unit.format_dimension(L),
        dimstyle=dim_style,
        layer="DIM_LINEAR",
    )
    draw_dimension(
        target,
        (ox, oy),
        (ox, oy + W),
        location=(ox - dim_offset, oy + W / 2.0),
        text_override=d_unit.format_dimension(W),
        dimstyle=dim_style,
        layer="DIM_LINEAR",
    )

    if title is None:
        title = f"Slab Plan — {slab.name}"
    draw_text(target, title, position=(ox, oy + W + dim_offset * 0.8), height=title_h, layer="TEXT")

    refs.update({"plan_origin": (ox, oy)})
    return refs


def section_view(
    target: Any,
    slab: SlabData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
    scale: Any | None = None,
    unit: Any | None = None,
) -> dict[str, Any]:
    """Draw a slab cross-section (a thin strip)."""
    ox, oy = origin
    L = slab.length_in
    t = slab.thickness_in
    cover = slab.cover_in

    scale = scale or getattr(slab, "scale", None)
    unit = unit or getattr(slab, "unit", None)
    is_metric = unit.is_metric if unit is not None else slab.is_metric

    from struct_draw.core.units import DrawingScale, DrawingUnit, SCALE_1_20, SCALE_1_IN
    from struct_draw.style.annotation_config import DEFAULT_ANNOTATION_CONFIG

    d_unit = unit or (DrawingUnit.MM if is_metric else DrawingUnit.IN)
    d_scale = scale or (SCALE_1_20 if is_metric else SCALE_1_IN)

    dim_offset = DEFAULT_ANNOTATION_CONFIG.dim_offset(d_scale, d_unit)
    title_h = DEFAULT_ANNOTATION_CONFIG.title_height(d_scale, d_unit)
    dim_style = "DIM_DETAIL" if is_metric else "Linear"

    refs: dict[str, Any] = {"origin": (ox, oy)}

    draw_concrete_outline(target, origin=(ox, oy), width=L, height=t, layer="CONC_OUTLINE")

    # Top + bottom rebar dots.
    y_bot = oy + cover
    y_top = oy + t - cover
    spacing = 150.0 if is_metric else 6.0
    dot_dia = 10.0 if is_metric else 0.375
    x = ox + cover
    while x <= ox + L - cover:
        draw_rebar_circle(target, (x, y_bot), diameter=dot_dia, layer="REBAR")
        draw_rebar_circle(target, (x, y_top), diameter=dot_dia, layer="REBAR")
        x += spacing

    # Thickness dimension.
    t_text = f"t = {t:.0f} mm" if is_metric else f"t = {t:.1f}\""
    draw_dimension(
        target,
        (ox, oy),
        (ox, oy + t),
        location=(ox - dim_offset, oy + t / 2.0),
        text_override=t_text,
        dimstyle=dim_style,
        layer="DIM_LINEAR",
    )

    if title is None:
        title = f"Slab Section — {slab.name}"
    draw_text(target, title, position=(ox, oy + t + dim_offset * 0.8), height=title_h, layer="TEXT")

    refs.update({"section_origin": (ox, oy)})
    return refs


__all__ = ["plan_view", "section_view"]