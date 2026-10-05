"""struct_draw.elements.beam — Section + elevation views for beams.

A beam section view draws the concrete outline, the stirrup
(polyline of the outer stirrup), the top and bottom longitudinal
bars (each as a single dot for a single layer or a row of dots
when bar coordinates are given), and the standard width / depth
linear dimensions.

A beam elevation view draws the beam as a long thin outline,
places stirrup symbols along its length, draws the longitudinal
top / bottom bars as horizontal lines, and emits a break-line
near one end if the elevation is "long" (so the user sees
``continues →``).
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
    draw_stirrup,
    draw_stirrup_hooked,
    draw_text,
)
from struct_draw.core.data import BeamData, Rebar
from struct_draw.core.primitives import draw_rectangle


# ---------------------------------------------------------------------------
# Section view
# ---------------------------------------------------------------------------


def _bar_positions(bar: Rebar, *, section_width: float, cover: float, tie_dia: float = 0.375, bar_dia: float = 0.625) -> list[float]:
    """Compute the x-positions of an evenly-spaced row of bar dots.

    Reads ``bar.quantity`` (or falls back to 1) and spreads the
    bars between ``cover + tie_dia + bar_dia / 2`` and ``section_width - cover - tie_dia - bar_dia / 2``.
    """
    n = max(1, int(getattr(bar, "quantity", 1) or 1))
    if n == 1:
        return [section_width / 2.0]
    x_left = cover + tie_dia + bar_dia / 2.0
    x_right = section_width - cover - tie_dia - bar_dia / 2.0
    if x_right <= x_left:
        return [section_width / 2.0]
    step = (x_right - x_left) / (n - 1)
    return [x_left + i * step for i in range(n)]


def section_view(
    target: Any,
    beam: BeamData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
    scale: Any | None = None,
    unit: Any | None = None,
) -> dict[str, Any]:
    """Draw a beam cross-section.

    The section shows:

    * concrete outline (closed rectangle),
    * double-line closed stirrup with 135° seismic hooks,
    * top and bottom longitudinal bars as a row of rebar dots,
    * linear width / depth dimensions,
    * the beam name as a label.

    Returns a metadata dict with the references produced during the
    draw.
    """
    from struct_draw.core.units import DrawingScale, DrawingUnit, SCALE_1_30, SCALE_1_2_IN
    from struct_draw.style.annotation_config import DEFAULT_ANNOTATION_CONFIG

    ox, oy = origin
    w = beam.section.width_in
    d = beam.section.depth_in
    cover = beam.section.cover_in

    is_m = getattr(unit, "is_metric", None)
    if is_m is None:
        is_m = beam.is_metric
    d_unit = unit or (DrawingUnit.MM if is_m else DrawingUnit.IN)
    d_scale = scale or getattr(beam, "scale", None) or (SCALE_1_30 if is_m else SCALE_1_2_IN)

    dim_offset = DEFAULT_ANNOTATION_CONFIG.dim_offset(d_scale, d_unit)
    title_height = DEFAULT_ANNOTATION_CONFIG.title_height(d_scale, d_unit)
    dim_style = "DIM_SECTION" if is_m else "DIM_SECTION"

    refs: dict[str, Any] = {"origin": (ox, oy), "width": w, "depth": d}

    # ----- Concrete outline.
    draw_concrete_outline(target, origin=(ox, oy), width=w, height=d, layer="CONC_OUTLINE")

    # ----- Top bars setup for geometry
    top_bars = list(beam.top_bars) if beam.top_bars else [_default_bar("#5" if not is_m else "T16", 2, "T")]
    corner_bar_dia = _bar_diameter(top_bars[0].size, is_metric=is_m) if top_bars else (0.5 if not is_m else 16.0)

    # ----- Stirrup (Double line).
    tie_size = getattr(beam.stirrups, "size", "#3") or "#3"
    tie_dia = _bar_diameter(tie_size, is_metric=is_m)
    sw = max(1.0, w - 2.0 * cover)
    sh = max(1.0, d - 2.0 * cover)
    if sw > 0 and sh > 0:
        draw_stirrup_hooked(
            target,
            width=sw,
            height=sh,
            origin=(ox + cover, oy + cover),
            tie_diameter=tie_dia,
            hook_length=max(6.0 * tie_dia, 60.0 if is_m else 3.0),
            corner_bar_diameter=corner_bar_dia,
            double_line=True,
            layer="STIRRUP",
        )

    # ----- Top bars (row of dots).
    for bar in top_bars:
        dia = _bar_diameter(bar.size, is_metric=is_m)
        top_y = oy + d - cover - tie_dia - dia / 2.0
        for x_local in _bar_positions(bar, section_width=w, cover=cover, tie_dia=tie_dia, bar_dia=dia):
            draw_rebar_circle(target, (ox + x_local, top_y), diameter=dia, layer="REBAR")

    # ----- Bottom bars (row of dots).
    bot_bars = list(beam.bottom_bars) if beam.bottom_bars else [_default_bar("#5" if not is_m else "T20", 2, "B")]
    for bar in bot_bars:
        dia = _bar_diameter(bar.size, is_metric=is_m)
        bot_y = oy + cover + tie_dia + dia / 2.0
        for x_local in _bar_positions(bar, section_width=w, cover=cover, tie_dia=tie_dia, bar_dia=dia):
            draw_rebar_circle(target, (ox + x_local, bot_y), diameter=dia, layer="REBAR")

    # ----- Linear dimensions (width below, depth on the left).
    draw_dimension(
        target,
        (ox, oy),
        (ox + w, oy),
        location=(ox + w / 2.0, oy - dim_offset),
        text_override=d_unit.format_dimension(w),
        dimstyle=dim_style,
        layer="DIM_LINEAR",
    )
    draw_dimension(
        target,
        (ox, oy),
        (ox, oy + d),
        location=(ox - dim_offset, oy + d / 2.0),
        text_override=d_unit.format_dimension(d),
        dimstyle=dim_style,
        layer="DIM_LINEAR",
    )

    # ----- Section title.
    if title is None:
        title = f"Section @ {beam.name}"
    title_y = oy - dim_offset * 2.4
    title_x = ox + w / 2.0 - len(title) * title_height * 0.28
    draw_text(target, title, position=(title_x, title_y), height=title_height, layer="TEXT")

    refs.update({"section_origin": (ox, oy)})
    return refs


# ---------------------------------------------------------------------------
# Elevation view
# ---------------------------------------------------------------------------


def elevation_view(
    target: Any,
    beam: BeamData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
    break_line_at: float | None = None,
    scale: Any | None = None,
    unit: Any | None = None,
) -> dict[str, Any]:
    """Draw a beam elevation (longitudinal view).

    The elevation shows:

    * the beam outline (long rectangle),
    * top + bottom longitudinal bars as horizontal lines,
    * stirrups drawn as short vertical lines at regular spacing,
    * a break line at ``break_line_at`` (if given),
    * a length dimension below the beam,
    * the beam name as a label.

    Returns a metadata dict with the references produced.
    """
    from struct_draw.core.units import DrawingScale, DrawingUnit, SCALE_1_50, SCALE_1_4_IN
    from struct_draw.style.annotation_config import DEFAULT_ANNOTATION_CONFIG

    ox, oy = origin
    w = beam.section.width_in
    d = beam.section.depth_in
    L = beam.length_in

    is_m = getattr(unit, "is_metric", None)
    if is_m is None:
        is_m = beam.is_metric
    d_unit = unit or (DrawingUnit.MM if is_m else DrawingUnit.IN)
    d_scale = scale or (SCALE_1_50 if is_m else SCALE_1_4_IN)

    dim_offset = DEFAULT_ANNOTATION_CONFIG.dim_offset(d_scale, d_unit)
    title_height = DEFAULT_ANNOTATION_CONFIG.title_height(d_scale, d_unit)
    dim_style = "DIM_ELEV" if is_m else "Linear"

    refs: dict[str, Any] = {"origin": (ox, oy), "length": L}

    # Beam outline (long rectangle, depth-as-thickness).
    draw_rectangle(target, origin=(ox, oy), width=L, height=d, layer="BEAM")

    # Top + bottom longitudinal bar lines.
    top_y = oy + d - beam.section.cover_in
    bot_y = oy + beam.section.cover_in
    bar_inset = 60.0 if is_m else 6.0
    for bar in list(beam.top_bars) or [_default_bar("#5" if not is_m else "T16", 1, "T")]:
        if bar.points:
            draw_rebar_bar(target, bar, layer="REBAR")
        else:
            draw_line(target, (ox + bar_inset, top_y), (ox + L - bar_inset, top_y), layer="REBAR")
    for bar in list(beam.bottom_bars) or [_default_bar("#5" if not is_m else "T20", 1, "B")]:
        if bar.points:
            draw_rebar_bar(target, bar, layer="REBAR")
        else:
            draw_line(target, (ox + bar_inset, bot_y), (ox + L - bar_inset, bot_y), layer="REBAR")

    # Stirrups (vertical short lines, evenly spaced).
    spacing = max(50.0 if is_m else 2.0, beam.stirrups.spacing_in)
    x = ox + spacing
    stirrup_inset = 10.0 if is_m else 0.5
    while x <= ox + L - spacing:
        draw_line(target, (x, oy + stirrup_inset), (x, oy + d - stirrup_inset), layer="STIRRUP")
        x += spacing

    # Length dimension.
    draw_dimension(
        target,
        (ox, oy),
        (ox + L, oy),
        location=(ox + L / 2.0, oy - dim_offset),
        text_override=d_unit.format_dimension(L),
        dimstyle=dim_style,
        layer="DIM_LINEAR",
    )

    # Optional break line.
    if break_line_at is not None:
        x_break = ox + break_line_at
        draw_break_line(target, p1=(x_break, oy), p2=(x_break, oy + d),
                        layer="BREAK_LINE")

    if title is None:
        title = f"Elevation of {beam.name}"
    draw_text(target, title, position=(ox, oy + d + dim_offset * 0.8), height=title_height, layer="TEXT")

    refs.update({"elevation_origin": (ox, oy)})
    return refs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_BAR_DIA_BY_DESIGNATOR: dict[str, float] = {
    "#3": 0.375,
    "#4": 0.500,
    "#5": 0.625,
    "#6": 0.750,
    "#7": 0.875,
    "#8": 1.000,
    "#9": 1.128,
    "#10": 1.270,
    "#11": 1.410,
    "#14": 1.693,
    "#18": 2.257,
}


def _bar_diameter(size: str, is_metric: bool = False) -> float:
    """Return the bar diameter (inches or mm) for a designator like ``"#5"`` or ``"T20"``.

    Falls back to ``0.625`` (in) or ``16.0`` (mm) for unknown sizes.
    """
    if is_metric:
        digits = "".join(c for c in size if c.isdigit())
        return float(digits) if digits else 16.0
    return _BAR_DIA_BY_DESIGNATOR.get(size, 0.625)


def _default_bar(size: str, quantity: int, prefix: str) -> Rebar:
    """Construct a placeholder :class:`Rebar` for default layouts."""
    return Rebar(
        mark=f"{prefix}1",
        size=size,
        quantity=quantity,
        length_in=0.0,
        points=(),
    )


__all__ = ["section_view", "elevation_view"]