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


def _bar_positions(bar: Rebar, *, section_width: float, cover: float, bar_dia: float = 0.625) -> list[float]:
    """Compute the x-positions of an evenly-spaced row of bar dots.

    Reads ``bar.quantity`` (or falls back to 1) and spreads the
    bars between ``cover + bar_dia / 2`` and ``section_width - cover - bar_dia / 2``.
    """
    n = max(1, int(getattr(bar, "quantity", 1) or 1))
    if n == 1:
        return [section_width / 2.0]
    x_left = cover + bar_dia / 2.0
    x_right = section_width - cover - bar_dia / 2.0
    step = (x_right - x_left) / (n - 1)
    return [x_left + i * step for i in range(n)]


def section_view(
    target: Any,
    beam: BeamData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
) -> dict[str, Any]:
    """Draw a beam cross-section.

    The section shows:

    * concrete outline (closed rectangle),
    * outer stirrup (closed polyline inside the cover),
    * top and bottom longitudinal bars as a row of rebar dots,
    * linear width / depth dimensions,
    * the beam name as a label.

    Returns a metadata dict with the references produced during the
    draw.
    """
    ox, oy = origin
    w = beam.section.width_in
    d = beam.section.depth_in
    cover = beam.section.cover_in

    refs: dict[str, Any] = {"origin": (ox, oy), "width": w, "depth": d}

    # ----- Concrete outline.
    draw_concrete_outline(target, origin=(ox, oy), width=w, height=d, layer="CONC_OUTLINE")

    # ----- Stirrup.
    sw = max(1.0, w - 2.0 * cover)
    sh = max(1.0, d - 2.0 * cover)
    if sw > 0 and sh > 0:
        draw_stirrup_hooked(
            target,
            width=sw,
            height=sh,
            origin=(ox + cover, oy + cover),
            hook_length=min(sw, sh) * 0.2,
            layer="STIRRUP",
        )

    # ----- Top bars (row of dots).
    top_bars = list(beam.top_bars) if beam.top_bars else [_default_bar("#5", 2, "T")]
    for bar in top_bars:
        dia = _bar_diameter(bar.size)
        top_y = oy + d - cover - dia / 2.0
        for x_local in _bar_positions(bar, section_width=w, cover=cover, bar_dia=dia):
            draw_rebar_circle(target, (ox + x_local, top_y), diameter=dia * 1.2, layer="REBAR")

    # ----- Bottom bars (row of dots).
    bot_bars = list(beam.bottom_bars) if beam.bottom_bars else [_default_bar("#5", 2, "B")]
    for bar in bot_bars:
        dia = _bar_diameter(bar.size)
        bot_y = oy + cover + dia / 2.0
        for x_local in _bar_positions(bar, section_width=w, cover=cover, bar_dia=dia):
            draw_rebar_circle(target, (ox + x_local, bot_y), diameter=dia * 1.2, layer="REBAR")

    # ----- Linear dimensions (width below, depth on the left).
    draw_dimension(
        target,
        (ox, oy),
        (ox + w, oy),
        location=(ox + w / 2.0, oy - 1.5),
        text_override=f"{w:.0f}\"",
        layer="DIM_LINEAR",
    )
    draw_dimension(
        target,
        (ox, oy),
        (ox, oy + d),
        location=(ox - 1.5, oy + d / 2.0),
        text_override=f"{d:.0f}\"",
        layer="DIM_LINEAR",
    )

    # ----- Section title.
    if title is None:
        title = f"Section @ {beam.name}"
    draw_text(target, title, position=(ox, oy - 3.0), height=0.30, layer="TEXT")

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
    ox, oy = origin
    w = beam.section.width_in
    d = beam.section.depth_in
    L = beam.length_in

    refs: dict[str, Any] = {"origin": (ox, oy), "length": L}

    # Beam outline (long rectangle, depth-as-thickness).
    draw_rectangle(target, origin=(ox, oy), width=L, height=d, layer="BEAM")

    # Top + bottom longitudinal bar lines.
    top_y = oy + d - beam.section.cover_in
    bot_y = oy + beam.section.cover_in
    for bar in list(beam.top_bars) or [_default_bar("#5", 1, "T")]:
        if bar.points:
            draw_rebar_bar(target, bar, layer="REBAR")
        else:
            draw_line(target, (ox + 6.0, top_y), (ox + L - 6.0, top_y), layer="REBAR")
    for bar in list(beam.bottom_bars) or [_default_bar("#5", 1, "B")]:
        if bar.points:
            draw_rebar_bar(target, bar, layer="REBAR")
        else:
            draw_line(target, (ox + 6.0, bot_y), (ox + L - 6.0, bot_y), layer="REBAR")

    # Stirrups (vertical short lines, evenly spaced).
    spacing = max(2.0, beam.stirrups.spacing_in)
    x = ox + spacing
    while x <= ox + L - spacing:
        draw_line(target, (x, oy + 0.5), (x, oy + d - 0.5), layer="STIRRUP")
        x += spacing

    # Length dimension.
    draw_dimension(
        target,
        (ox, oy),
        (ox + L, oy),
        location=(ox + L / 2.0, oy - 2.0),
        text_override=f"{L:.0f}\"",
        layer="DIM_LINEAR",
    )

    # Optional break line.
    if break_line_at is not None:
        x_break = ox + break_line_at
        draw_break_line(target, p1=(x_break, oy), p2=(x_break, oy + d),
                        layer="BREAK_LINE")

    if title is None:
        title = f"Elevation of {beam.name}"
    draw_text(target, title, position=(ox, oy + d + 1.5), height=0.30, layer="TEXT")

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


def _bar_diameter(size: str) -> float:
    """Return the bar diameter (inches) for a designator like ``"#5"``.

    Falls back to ``0.625`` (i.e. ``#5``) for unknown sizes.
    """
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