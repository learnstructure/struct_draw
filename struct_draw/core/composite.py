"""struct_draw.core.composite — Reusable rebar / concrete drawing helpers.

Composite helpers wrap one or more :mod:`struct_draw.core.primitives`
calls into a single semantic drawing operation. They:

* pick the **correct layer** for the entity (so callers don't
  have to know that rebar goes on ``REBAR``, stirrups on
  ``STIRRUP``, etc.),
* apply standard drafting offsets (cover, hook geometry, leader
  offsets, etc.),
* apply the high-quality drawing conventions captured from the
  project references (e.g. ``references/footing.py``).

Element functions (``elements/``) compose their views from these
helpers; this is the layer at which "what does a beam section look
like" is encoded.
"""

from __future__ import annotations

from typing import Any, Sequence

from struct_draw.core.data import Rebar, Stirrup
from struct_draw.core.primitives import (
    draw_circle,
    draw_dim_linear,
    draw_hatch,
    draw_leader,
    draw_line,
    draw_polyline,
    draw_rectangle,
    draw_text,
)


# ---------------------------------------------------------------------------
# Concrete outlines
# ---------------------------------------------------------------------------


def draw_concrete_outline(
    target: Any,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    width: float,
    height: float,
    layer: str = "CONC_OUTLINE",
    close: bool = True,
) -> Any:
    """Draw a rectangular concrete outline.

    The outline is the visible silhouette of the member in section
    or plan.
    """
    return draw_rectangle(
        target,
        origin=origin,
        width=width,
        height=height,
        close=close,
        layer=layer,
    )


# ---------------------------------------------------------------------------
# Stirrups
# ---------------------------------------------------------------------------


def draw_stirrup(
    target: Any,
    *,
    width: float,
    height: float,
    origin: tuple[float, float] = (0.0, 0.0),
    layer: str = "STIRRUP",
) -> Any:
    """Draw a rectangular stirrup as a closed polyline.

    The stirrup's centerline is offset from the concrete face by
    ``cover + stirrup_dia/2`` (the caller is expected to have
    already applied cover and bar diameter).
    """
    if width <= 0 or height <= 0:
        # Defer silently; the caller may be drawing a column too
        # narrow for a stirrup outline.
        return None
    x0, y0 = origin
    pts = [
        (x0, y0),
        (x0 + width, y0),
        (x0 + width, y0 + height),
        (x0, y0 + height),
        (x0, y0),
    ]
    return draw_polyline(target, pts, close=True, layer=layer)


def draw_stirrup_hooked(
    target: Any,
    *,
    width: float,
    height: float,
    origin: tuple[float, float] = (0.0, 0.0),
    hook_length: float = 3.0,
    corner: str = "top_left",
    tie_diameter: float | None = None,
    double_line: bool = True,
    layer: str = "STIRRUP",
) -> list[Any]:
    """Draw a professional stirrup with realistic parallel 135° hooks turning into the concrete core.

    Supports both double-line (standard CAD detailing) and single-line representation.
    """
    if width <= 0 or height <= 0:
        return []

    is_metric = width >= 100.0 or height >= 100.0
    t = tie_diameter if (tie_diameter is not None and tie_diameter > 0) else (10.0 if is_metric else 0.375)

    from struct_draw.core.stirrup import StirrupGeometry

    st = StirrupGeometry(
        diameter=t,
        width=width,
        depth=height,
        origin=origin,
        hook_length=hook_length,
        hook_corner=corner if corner != "all" else "top_left",
        double_line=double_line,
        layer=layer,
    )
    out = st.draw(target)
    if corner in ("top_right", "top_both") and corner != "top_left":
        st_r = StirrupGeometry(
            diameter=t,
            width=width,
            depth=height,
            origin=origin,
            hook_length=hook_length,
            hook_corner="top_right",
            double_line=False,
            layer=layer,
        )
        out.extend(st_r.draw(target))
    return out


def draw_beam_section(
    target: Any,
    *,
    center_x: float,
    top_y: float,
    width: float,
    height: float,
    is_metric: bool = True,
    layer_beam: str = "Beam",
    layer_stirrup: str = "Stirrup",
    layer_rebar: str = "Rebar_hatch",
) -> list[Any]:
    """Draw a standard beam cross-section template with concrete outline, stirrup with parallel 135° seismic hooks, and longitudinal rebar circles.

    Can be used consistently for plinth beams, foundation beams, grade beams, etc.
    """
    if width <= 0 or height <= 0:
        return []

    out: list[Any] = []

    # 1. Outer concrete box
    b_pts = [
        (center_x - width / 2.0, top_y),
        (center_x + width / 2.0, top_y),
        (center_x + width / 2.0, top_y - height),
        (center_x - width / 2.0, top_y - height),
    ]
    p_beam = draw_polyline(target, b_pts, close=True, layer=layer_beam)
    if p_beam:
        out.append(p_beam)

    # 2. Stirrup inner box with parallel 135° hooks
    st_off = 25.0 if is_metric else 1.0
    sw = max(1.0, width - 2.0 * st_off)
    sh = max(1.0, height - 2.0 * st_off)
    sx0 = center_x - width / 2.0 + st_off
    sy0 = top_y - height + st_off
    hook_len = 75.0 if is_metric else 3.0

    st_ents = draw_stirrup_hooked(
        target,
        width=sw,
        height=sh,
        origin=(sx0, sy0),
        hook_length=hook_len,
        corner="top_left",
        layer=layer_stirrup,
    )
    if st_ents:
        out.extend(st_ents)

    # 3. Longitudinal rebar dots
    b_dot = 5.0 if is_metric else 0.25
    x_coords = (
        center_x - width / 2.0 + st_off + b_dot,
        center_x,
        center_x + width / 2.0 - st_off - b_dot,
    )
    y_coords = (
        top_y - st_off - b_dot,
        top_y - height + st_off + b_dot,
    )
    for cx in x_coords:
        for cy in y_coords:
            c_ent = draw_rebar_circle(target, (cx, cy), diameter=b_dot * 2.0, layer=layer_rebar)
            if c_ent:
                out.append(c_ent)

    return out


# ---------------------------------------------------------------------------
# Rebar bars
# ---------------------------------------------------------------------------


def draw_rebar_bar(
    target: Any,
    bar: Rebar,
    *,
    layer: str = "REBAR",
) -> list[Any]:
    """Draw a single rebar polyline from its ``points`` (with optional hooks).

    Returns the list of entities drawn (polyline + optional hook
    stubs). If ``bar.points`` is empty, an empty list is returned.
    """
    if not bar.points:
        return []
    out: list[Any] = []
    poly = draw_polyline(target, list(bar.points), close=False, layer=layer)
    out.append(poly)
    if bar.hook_start and len(bar.points) >= 1:
        sx, sy = bar.points[0]
        out.append(draw_line(target, (sx, sy), (sx, sy + 0.5), layer="HOOK"))
    if bar.hook_end and len(bar.points) >= 1:
        ex, ey = bar.points[-1]
        out.append(draw_line(target, (ex, ey), (ex, ey + 0.5), layer="HOOK"))
    return out


def draw_rebar_circle(
    target: Any,
    center: tuple[float, float],
    diameter: float = 0.25,
    *,
    layer: str = "REBAR_HATCH",
) -> Any:
    """Draw the small filled circle used to represent a rebar in section."""
    if diameter <= 0:
        raise ValueError("draw_rebar_circle requires positive diameter.")
    return draw_circle(target, center, radius=diameter / 2.0, layer=layer)


# ---------------------------------------------------------------------------
# Bar marks / annotations
# ---------------------------------------------------------------------------


def draw_bar_mark(
    target: Any,
    *,
    position: tuple[float, float],
    text: str,
    leader_to: tuple[float, float] | None = None,
    text_height: float = 0.10,
    layer: str = "BAR_MARK",
) -> list[Any]:
    """Draw a bar mark: a small text label with an optional leader.

    ``position`` is the location of the text label (not the bar).
    ``leader_to`` is an optional (x, y) of the bar that the leader
    points at.
    """
    out: list[Any] = []
    if leader_to is not None:
        # Leader vertex order: leader_to → small bend → position
        bend = (position[0], leader_to[1])
        out.append(draw_leader(target, [leader_to, bend, position], text="", layer=layer))
    out.append(
        draw_text(
            target,
            text,
            position=position,
            height=text_height,
            layer=layer,
        )
    )
    return out


def draw_level_marker(
    target: Any,
    *,
    anchor: tuple[float, float],
    direction: str,
    length: float = 6.0,
    label: str,
    label_offset: tuple[float, float] = (-2.0, -0.5),
    text_height: float = 0.20,
    line_layer: str = "LEVEL",
    text_layer: str = "TEXT",
) -> list[Any]:
    """Draw an "GL" / "PL" level marker (line + label).

    ``direction`` is one of ``"left"``, ``"right"``, ``"both"``.
    ``anchor`` is the point on the member at the level.
    """
    out: list[Any] = []
    x, y = anchor
    if direction in ("left", "both"):
        out.append(draw_line(target, (x - length, y), (x, y), layer=line_layer))
    if direction in ("right", "both"):
        out.append(draw_line(target, (x, y), (x + length, y), layer=line_layer))
    label_pos = (x + label_offset[0], y + label_offset[1])
    out.append(draw_text(target, label, position=label_pos, height=text_height, layer=text_layer))
    return out


# ---------------------------------------------------------------------------
# Break line (shorthand for "more of the member continues here")
# ---------------------------------------------------------------------------


def draw_break_line(
    target: Any,
    *,
    p1: tuple[float, float],
    p2: tuple[float, float],
    layer: str = "BREAK_LINE",
    jog: float = 0.5,
) -> list[Any]:
    """Draw a freehand break line between ``p1`` and ``p2``.

    Used at the top of long members (column / beam elevations) to
    indicate "continues above". The break is a small S-curve
    approximated by a polyline.
    """
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2:
        # Vertical break: jog horizontally.
        mid_y = 0.5 * (y1 + y2)
        pts = [
            (x1, y1),
            (x1 - jog, mid_y),
            (x1, mid_y),
            (x1 + jog, mid_y),
            (x1, y2),
        ]
    else:
        mid_x = 0.5 * (x1 + x2)
        pts = [
            (x1, y1),
            (mid_x, y1 + jog),
            (mid_x, y1),
            (mid_x, y2),
            (x2, y2),
        ]
    return [draw_polyline(target, pts, close=False, layer=layer)]


# ---------------------------------------------------------------------------
# Section-cut symbol
# ---------------------------------------------------------------------------


def draw_section_cut_symbol(
    target: Any,
    *,
    center: tuple[float, float],
    letter: str = "A",
    size: float = 0.5,
    layer: str = "SECTION_CUT",
) -> list[Any]:
    """Draw an ACI 318 section-cut symbol: a circle with a centered letter."""
    out: list[Any] = []
    out.append(draw_circle(target, center, radius=size, layer=layer))
    out.append(
        draw_text(
            target,
            letter,
            position=(center[0], center[1] - size * 0.35),
            height=size * 0.7,
            layer=layer,
        )
    )
    return out


# ---------------------------------------------------------------------------
# Convenience: layer-aware dimension with text override
# ---------------------------------------------------------------------------


def draw_dimension(
    target: Any,
    p1: tuple[float, float],
    p2: tuple[float, float],
    location: tuple[float, float],
    *,
    text_override: str | None = None,
    dimstyle: str = "Linear",
    layer: str = "DIM_LINEAR",
) -> Any:
    """Draw a linear dimension with an optional text override."""
    return draw_dim_linear(
        target,
        p1=p1,
        p2=p2,
        location=location,
        text_override=text_override,
        dimstyle=dimstyle,
        layer=layer,
    )


__all__ = [
    "draw_concrete_outline",
    "draw_stirrup",
    "draw_stirrup_hooked",
    "draw_beam_section",
    "draw_rebar_bar",
    "draw_rebar_circle",
    "draw_bar_mark",
    "draw_level_marker",
    "draw_break_line",
    "draw_section_cut_symbol",
    "draw_dimension",
    "draw_leader",
    "draw_hatch",
]