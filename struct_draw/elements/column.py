"""struct_draw.elements.column — Section + elevation views for columns.

A column section view shows the concrete outline, the stirrup
outline, and the longitudinal bars at the corners + sides.

A column elevation view shows the column outline (long
rectangle), the longitudinal bar lines, evenly-spaced stirrups,
and a break-line near the top of long columns.
"""

from __future__ import annotations

from typing import Any

from struct_draw.core.composite import (
    draw_break_line,
    draw_concrete_outline,
    draw_dimension,
    draw_line,
    draw_polyline,
    draw_rebar_bar,
    draw_rebar_circle,
    draw_stirrup_hooked,
    draw_text,
)
from struct_draw.core.data import ColumnData, Rebar
from struct_draw.core.primitives import draw_rectangle


def section_view(
    target: Any,
    column: ColumnData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
) -> dict[str, Any]:
    """Draw a column cross-section."""
    ox, oy = origin
    w = column.section.width_in
    d = column.section.depth_in
    cover = column.section.cover_in

    refs: dict[str, Any] = {"origin": (ox, oy)}

    draw_concrete_outline(target, origin=(ox, oy), width=w, height=d, layer="COLUMN")

    # Stirrup (assuming #3 bar unless the data says otherwise).
    stirrup_dia = 0.375
    sw = max(0.0, w - 2.0 * (cover + stirrup_dia / 2.0))
    sh = max(0.0, d - 2.0 * (cover + stirrup_dia / 2.0))
    if sw > 0 and sh > 0:
        draw_stirrup_hooked(
            target,
            width=sw,
            height=sh,
            origin=(ox + (w - sw) / 2.0, oy + (d - sh) / 2.0),
            hook_length=min(sw, sh) * 0.2,
            layer="STIRRUP",
        )

    # Longitudinal bars (corners + sides). Default: 4 corners if none given.
    bars = list(column.longitudinal_bars) or [_corner_bar("C", i + 1) for i in range(4)]
    for i, bar in enumerate(bars):
        x_local, y_local = _bar_xy(i, len(bars), w, d, cover)
        dia = _bar_diameter(bar.size)
        draw_rebar_circle(target, (ox + x_local, oy + y_local), diameter=dia * 1.2, layer="REBAR")

    # Linear dimensions.
    draw_dimension(target, (ox, oy), (ox + w, oy),
                    location=(ox + w / 2.0, oy - 1.5),
                    text_override=f"{w:.0f}\"", layer="DIM_LINEAR")
    draw_dimension(target, (ox, oy), (ox, oy + d),
                    location=(ox - 1.5, oy + d / 2.0),
                    text_override=f"{d:.0f}\"", layer="DIM_LINEAR")

    if title is None:
        title = f"Section @ {column.name}"
    draw_text(target, title, position=(ox, oy - 3.0), height=0.30, layer="TEXT")

    refs.update({"section_origin": (ox, oy)})
    return refs


def elevation_view(
    target: Any,
    column: ColumnData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
    break_line_at: float | None = None,
) -> dict[str, Any]:
    """Draw a column elevation (longitudinal view)."""
    ox, oy = origin
    w = column.section.width_in
    d = column.section.depth_in
    H = column.height_in

    refs: dict[str, Any] = {"origin": (ox, oy)}

    draw_rectangle(target, origin=(ox, oy), width=w, height=H, layer="COLUMN")

    # Longitudinal bars: at the four corners.
    for (x_local, _) in [(_bar_xy(i, 4, w, d, column.section.cover_in)[0], 0) for i in range(4)]:
        bar = _corner_bar("C", 1)
        bar_pts = ((ox + x_local, oy + 6.0), (ox + x_local, oy + H - 6.0))
        bar = Rebar(mark="L1", size=bar.size, quantity=1, length_in=H,
                     points=bar_pts)
        draw_rebar_bar(target, bar, layer="REBAR")

    # Stirrups (horizontal cross-ties).
    spacing = max(4.0, column.stirrups.spacing_in)
    y = oy + spacing
    while y <= oy + H - spacing:
        draw_line(target, (ox + 0.5, y), (ox + w - 0.5, y), layer="STIRRUP")
        y += spacing

    # Length dimension (left of column).
    draw_dimension(target, (ox, oy), (ox, oy + H),
                    location=(ox - 1.5, oy + H / 2.0),
                    text_override=f"{H:.0f}\"", layer="DIM_LINEAR")

    if break_line_at is not None:
        x_break = ox + break_line_at
        draw_break_line(target, p1=(x_break, oy), p2=(x_break, oy + H),
                        layer="BREAK_LINE")

    if title is None:
        title = f"Elevation of {column.name}"
    draw_text(target, title, position=(ox + w + 2.0, oy + H + 1.5),
              height=0.30, layer="TEXT")

    refs.update({"elevation_origin": (ox, oy)})
    return refs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bar_xy(index: int, total: int, w: float, d: float, cover: float) -> tuple[float, float]:
    """Return the (x_local, y_local) of bar ``index`` of ``total``.

    For ``total == 4`` the four corners are used. For other
    counts, bars are evenly spaced around the inside perimeter
    starting from the bottom-left corner and going clockwise.
    """
    if total == 4:
        corners = [
            (cover, cover),
            (w - cover, cover),
            (w - cover, d - cover),
            (cover, d - cover),
        ]
        return corners[index % 4]
    # Generic placement: evenly around the inside perimeter.
    perimeter = 2.0 * (w + d - 4.0 * cover)
    s = perimeter * index / max(total, 1)
    s = s % perimeter
    if s < (w - 2 * cover):
        return (cover + s, cover)
    s -= (w - 2 * cover)
    if s < (d - 2 * cover):
        return (w - cover, cover + s)
    s -= (d - 2 * cover)
    if s < (w - 2 * cover):
        return (w - cover - s, d - cover)
    s -= (w - 2 * cover)
    return (cover, d - cover - s)


def _corner_bar(prefix: str, idx: int) -> Rebar:
    """A placeholder longitudinal bar used for default column layouts."""
    return Rebar(mark=f"{prefix}{idx}", size="#8", quantity=1, length_in=0.0)


_BAR_DIA_BY_DESIGNATOR: dict[str, float] = {
    "#3": 0.375, "#4": 0.500, "#5": 0.625, "#6": 0.750,
    "#7": 0.875, "#8": 1.000, "#9": 1.128, "#10": 1.270,
    "#11": 1.410, "#14": 1.693, "#18": 2.257,
}


def _bar_diameter(size: str) -> float:
    return _BAR_DIA_BY_DESIGNATOR.get(size, 1.0)


__all__ = ["section_view", "elevation_view"]