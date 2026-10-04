"""struct_draw.elements.staircase — Plan + section views for staircases.

This module implements detailed, production-ready structural drawing functions
for staircases (waist-slab staircases) matching and exceeding the quality of
``references/staircase.py``.

Key features:
* Accurate geometry for waist slab, treads, risers, and landings.
* Left and right landing / main support beams.
* Complete reinforcement detailing:
  - Scissor (crank / cross) longitudinal rebar at landing-flight junctions.
  - Extension bars maintaining Ld = 60 * dia across scissor junctions.
  - Perfectly aligned transverse distribution rebar dots resting against main bars along inclined waist slab.
  - Step nosing bars and nosing stirrups / binders in steps.
* Multileader callouts for main bars, extra bars, distribution bars, beams, and nosing bars.
* Grid line axes with circular bubble markers.
* Complete dimensioning for step risers/treads, landings, going, grid span, and height.
* Plan view with continuous single-polyline UP walkline across flights/landings, section cut line A-A, and centered title.
"""

from __future__ import annotations

import math
from typing import Any

from struct_draw.core.composite import (
    draw_break_line,
    draw_dimension,
    draw_leader,
    draw_line,
    draw_polyline,
    draw_rebar_circle,
    draw_section_cut_symbol,
    draw_text,
)
from struct_draw.core.data import StaircaseData
from struct_draw.core.primitives import draw_circle, draw_rectangle


def _clean_text(txt: str) -> str:
    """Replace non-rendering unicode symbols with standard CAD text."""
    if not txt:
        return ""
    return txt.replace("φ", "mm dia").replace("Φ", "mm dia").replace("ϕ", "mm dia")


def _format_rebar_size(bar_dia_in: float, is_metric: bool = False) -> str:
    """Format rebar size/diameter string."""
    if is_metric or bar_dia_in >= 6.0:
        val_str = f"{int(bar_dia_in)}" if bar_dia_in.is_integer() else f"{bar_dia_in:.1f}"
        return f"{val_str}mm dia"
    bar_map = {
        0.3125: "#2",
        0.375: "#3",
        0.5: "#4",
        0.625: "#5",
        0.75: "#6",
        0.875: "#7",
        1.0: "#8",
    }
    for val, size in bar_map.items():
        if abs(bar_dia_in - val) < 0.05:
            return size
    if bar_dia_in.is_integer():
        return f"{int(bar_dia_in)}mm dia"
    return f'{bar_dia_in:.2f}"'


def _format_dim(val: float, is_metric: bool = False, include_unit: bool = False) -> str:
    """Format dimension value string."""
    if is_metric or val >= 300.0:
        if include_unit:
            return f"{int(val)}mm" if val.is_integer() else f"{val:.1f}mm"
        return f"{int(val)}" if val.is_integer() else f"{val:.1f}"
    if val.is_integer():
        return f'{int(val)}"'
    return f'{val:.1f}"'


def line_intersection(
    p1: tuple[float, float], p2: tuple[float, float],
    p3: tuple[float, float], p4: tuple[float, float]
) -> tuple[float, float]:
    """Find 2D intersection point of line (p1-p2) and line (p3-p4)."""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-9:
        return (x2, y2)

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def section_view(
    target: Any,
    stair: StaircaseData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
    scale: Any | None = None,
    unit: Any | None = None,
) -> dict[str, Any]:
    """Draw a detailed RCC staircase section view (Flight elevation with reinforcement).

    Parameters
    ----------
    target
        DXF modelspace or drawing target.
    stair
        :class:`StaircaseData` object with geometrical & structural parameters.
    origin
        (x, y) offset for the view.
    title
        Optional view title override.
    """
    ox, oy = origin
    scale = scale or getattr(stair, "scale", None)
    unit = unit or getattr(stair, "unit", None)
    is_metric = unit.is_metric if unit is not None else stair.is_metric

    # Geometry parameters
    beam_left_w = stair.beam_left_width_in
    beam_left_h = stair.beam_left_depth_in
    beam_right_w = stair.beam_right_width_in
    beam_right_h = stair.beam_right_depth_in

    waist = stair.slab_thickness_in
    cover = stair.cover_in
    tread = stair.tread_depth_in
    riser = stair.riser_height_in
    n_riser = max(2, stair.num_risers)
    d1 = stair.bottom_landing_depth_in
    d2 = stair.top_landing_depth_in

    main_dia = stair.main_bar_dia_in
    main_spacing = stair.main_bar_spacing_in
    dist_dia = stair.dist_bar_dia_in
    dist_spacing = stair.dist_bar_spacing_in
    nosing_dia = stair.nosing_bar_dia_in

    going = (n_riser - 1) * tread
    grid = d1 + d2 + going
    height = n_riser * riser

    theta = math.atan((height - riser) / going) if going > 0 else 0.0

    refs: dict[str, Any] = {"origin": (ox, oy)}

    # -----------------------------------------------------------------------
    # 1. Grid Lines & Axis Bubbles
    # -----------------------------------------------------------------------
    ext_top = height + (300.0 if is_metric else 12.0)
    ext_bot = 1000.0 if is_metric else 40.0
    if scale is not None or unit is not None:
        from struct_draw.core.units import DrawingScale, DrawingUnit, SCALE_1_25, SCALE_1_IN
        from struct_draw.style.annotation_config import DEFAULT_ANNOTATION_CONFIG
        d_unit = unit or (DrawingUnit.MM if is_metric else DrawingUnit.IN)
        d_scale = scale or (SCALE_1_25 if is_metric else SCALE_1_IN)
        text_sz = DEFAULT_ANNOTATION_CONFIG.text_height(d_scale, d_unit)
        st_sz = DEFAULT_ANNOTATION_CONFIG.dim_text_height(d_scale, d_unit)
        bubble_rad = DEFAULT_ANNOTATION_CONFIG.bubble_radius(d_scale, d_unit)
    else:
        bubble_rad = 100.0 if is_metric else 4.0
        text_sz = 120.0 if is_metric else 5.0
        st_sz = 80.0 if is_metric else 3.5

    # Grid 1 (Left)
    draw_line(target, (ox, oy - ext_bot - beam_left_h), (ox, oy + ext_top), layer="CENTERLINE")
    draw_circle(target, (ox, oy + ext_top + bubble_rad), radius=bubble_rad, layer="Dimension")
    draw_text(target, "1", position=(ox - bubble_rad * 0.4, oy + ext_top + bubble_rad * 0.3), height=text_sz, layer="Text")

    # Grid 2 (Right)
    draw_line(target, (ox + grid, oy - ext_bot - beam_left_h), (ox + grid, oy + ext_top), layer="CENTERLINE")
    draw_circle(target, (ox + grid, oy + ext_top + bubble_rad), radius=bubble_rad, layer="Dimension")
    draw_text(target, "2", position=(ox + grid - bubble_rad * 0.4, oy + ext_top + bubble_rad * 0.3), height=text_sz, layer="Text")

    # -----------------------------------------------------------------------
    # 2. Support Beams (Left & Right)
    # -----------------------------------------------------------------------
    bl_pts = [
        (ox + beam_left_w / 2.0, oy),
        (ox - beam_left_w / 2.0, oy),
        (ox - beam_left_w / 2.0, oy - beam_left_h),
        (ox + beam_left_w / 2.0, oy - beam_left_h),
        (ox + beam_left_w / 2.0, oy - waist),
    ]
    draw_polyline(target, bl_pts, close=False, layer="Beam")

    br_pts = [
        (ox + grid - beam_right_w / 2.0, oy + height),
        (ox + grid + beam_right_w / 2.0, oy + height),
        (ox + grid + beam_right_w / 2.0, oy + height - beam_right_h),
        (ox + grid - beam_right_w / 2.0, oy + height - beam_right_h),
        (ox + grid - beam_right_w / 2.0, oy + height - waist),
    ]
    draw_polyline(target, br_pts, close=False, layer="Beam")

    # Beam center stirrup outlines
    draw_rectangle(target, origin=(ox - beam_left_w / 2.0 + cover, oy - beam_left_h + cover),
                   width=max(1.0, beam_left_w - 2 * cover), height=max(1.0, beam_left_h - 2 * cover), layer="Stirrup")
    draw_rectangle(target, origin=(ox + grid - beam_right_w / 2.0 + cover, oy + height - beam_right_h + cover),
                   width=max(1.0, beam_right_w - 2 * cover), height=max(1.0, beam_right_h - 2 * cover), layer="Stirrup")

    # -----------------------------------------------------------------------
    # 3. Slab Outline & Steps (Treads & Risers)
    # -----------------------------------------------------------------------
    # Top face lines
    draw_line(target, (ox + beam_left_w / 2.0, oy), (ox + d1, oy), layer="Slab")
    draw_line(target, (ox + grid - d2, oy + height), (ox + grid - beam_right_w / 2.0, oy + height), layer="Slab")

    # Steps polyline
    for i in range(n_riser - 1):
        step_pts = [
            (ox + d1 + i * tread, oy + i * riser),
            (ox + d1 + i * tread, oy + (i + 1) * riser),
            (ox + d1 + (i + 1) * tread, oy + (i + 1) * riser),
        ]
        draw_polyline(target, step_pts, close=False, layer="Slab")

    draw_line(target, (ox + grid - d2, oy + height - riser), (ox + grid - d2, oy + height), layer="Slab")

    # Soffit lines
    b1_p1 = (ox + beam_left_w / 2.0, oy - waist)
    b1_p2 = (ox + d1, oy - waist)

    dx_so = waist * math.sin(theta)
    dy_so = -waist * math.cos(theta)
    b2_p1 = (ox + d1 + dx_so, oy + dy_so)
    b2_p2 = (ox + grid - d2 + dx_so, oy + height - riser + dy_so)

    b3_p1 = (ox + grid - d2, oy + height - waist)
    b3_p2 = (ox + grid - beam_right_w / 2.0, oy + height - waist)

    pi_b1_b2 = line_intersection(b1_p1, (ox + d1 + 2 * dx_so, oy - waist), b2_p1, b2_p2)
    pi_b2_b3 = line_intersection(b2_p1, b2_p2, (ox + grid - d2 - 2 * dx_so, oy + height - waist), b3_p2)

    draw_line(target, b1_p1, pi_b1_b2, layer="Slab")
    draw_line(target, pi_b1_b2, pi_b2_b3, layer="Slab")
    draw_line(target, pi_b2_b3, b3_p2, layer="Slab")

    # -----------------------------------------------------------------------
    # 4. Scissor Reinforcement & Extension Bars
    # -----------------------------------------------------------------------
    # Offset vectors for cover & waist
    dx_cv = cover * math.sin(theta)
    dy_cv = -cover * math.cos(theta)

    dx_b = (waist - cover) * math.sin(theta)
    dy_b = -(waist - cover) * math.cos(theta)

    # Scissor Junction Intersections
    tan_t = math.tan(theta) if theta > 0 else 0.001

    # Junction 1 Top (rt1: y = oy - cover, and rb2)
    x_int_j1_top = (ox + d1 + dx_b) + ((oy - cover) - (oy + dy_b)) / tan_t
    P_j1_top = (x_int_j1_top, oy - cover)

    # Junction 1 Bottom (rb1: y = oy - waist + cover, and rt2)
    x_int_j1_bot = (ox + d1 + dx_cv) + ((oy - waist + cover) - (oy + dy_cv)) / tan_t
    P_j1_bot = (x_int_j1_bot, oy - waist + cover)

    # Junction 2 Bottom (rb2 and rt3: y = oy + height - cover)
    x_int_j2_bot = (ox + d1 + dx_b) + ((oy + height - cover) - (oy + dy_b)) / tan_t
    P_j2_bot = (x_int_j2_bot, oy + height - cover)

    # Junction 2 Top (rt2 and rb3: y = oy + height - waist + cover)
    x_int_j2_top = (ox + d1 + dx_cv) + ((oy + height - waist + cover) - (oy + dy_cv)) / tan_t
    P_j2_top = (x_int_j2_top, oy + height - waist + cover)

    anch_depth = 250.0 if is_metric else 10.0

    # Scissor Main Polyline 1 (Top of bot landing -> Scissor down waist soffit -> Top of top landing)
    r1_pts = [
        (ox - beam_left_w / 2.0 + cover, oy - cover - anch_depth),
        (ox - beam_left_w / 2.0 + cover, oy - cover),
        P_j1_top,
        P_j2_bot,
        (ox + grid + beam_right_w / 2.0 - cover, oy + height - cover),
        (ox + grid + beam_right_w / 2.0 - cover, oy + height - cover - anch_depth),
    ]
    draw_polyline(target, r1_pts, close=False, layer="Rebar")

    # Scissor Main Polyline 2 (Bottom of bot landing -> Scissor up waist top -> Bottom of top landing)
    r2_pts = [
        (ox - beam_left_w / 2.0 + 2 * cover, oy - cover - anch_depth),
        (ox - beam_left_w / 2.0 + 2 * cover, oy - waist + cover),
        P_j1_bot,
        P_j2_top,
        (ox + grid + beam_right_w / 2.0 - 2 * cover, oy + height - waist + cover),
        (ox + grid + beam_right_w / 2.0 - 2 * cover, oy + height - cover - anch_depth),
    ]
    draw_polyline(target, r2_pts, close=False, layer="Rebar")

    # Extension bars maintaining Ld = 60 * main_dia
    Ld = 60.0 * main_dia

    # Ext 1: past P_j1_top down into waist soffit
    ext1_end = (P_j1_top[0] + Ld * math.cos(theta), P_j1_top[1] + Ld * math.sin(theta))
    draw_line(target, P_j1_top, ext1_end, layer="Rebar")

    # Ext 4: past P_j2_bot down-left into waist soffit
    ext4_end = (P_j2_bot[0] - Ld * math.cos(theta), P_j2_bot[1] - Ld * math.sin(theta))
    draw_line(target, P_j2_bot, ext4_end, layer="Rebar")

    # -----------------------------------------------------------------------
    # 4b. Extra Support Bars (Secondary Rebar Layer)
    # -----------------------------------------------------------------------
    extra_off = cover + main_dia + dist_dia + (5.0 if is_metric else 0.2)

    # Lower end extra bar (above bottom transverse bars at lower end of flight)
    y_extra_bot = oy - waist + extra_off
    dx_soffit_extra = (waist - extra_off) * math.sin(theta)
    dy_soffit_extra = -(waist - extra_off) * math.cos(theta)
    x_bot_junc = (ox + d1 + dx_soffit_extra) + (-waist + extra_off - dy_soffit_extra) / tan_t if tan_t > 0 else ox + d1
    P_bot_extra_junc = (x_bot_junc, y_extra_bot)

    p_bot_extra_sloped_end = (
        P_bot_extra_junc[0] + Ld * math.cos(theta),
        P_bot_extra_junc[1] + Ld * math.sin(theta),
    )
    p_bot_extra_landing_end = (
        P_bot_extra_junc[0] - Ld,
        y_extra_bot,
    )
    extra_bot_pts = [
        p_bot_extra_landing_end,
        P_bot_extra_junc,
        p_bot_extra_sloped_end,
    ]
    draw_polyline(target, extra_bot_pts, close=False, layer="Rebar")

    # Upper end extra bar (below top transverse bars at upper end of flight)
    y_extra_top = oy + height - extra_off
    dx_extra_top = extra_off * math.sin(theta)
    dy_extra_top = -extra_off * math.cos(theta)
    x_top_junc = (ox + d1 + dx_extra_top) + (height - extra_off - dy_extra_top) / tan_t if tan_t > 0 else ox + grid - d2
    P_top_extra_junc = (x_top_junc, y_extra_top)

    p_top_extra_sloped_end = (
        P_top_extra_junc[0] - Ld * math.cos(theta),
        P_top_extra_junc[1] - Ld * math.sin(theta),
    )
    p_top_extra_landing_end = (
        P_top_extra_junc[0] + Ld,
        y_extra_top,
    )
    extra_top_pts = [
        p_top_extra_sloped_end,
        P_top_extra_junc,
        p_top_extra_landing_end,
    ]
    draw_polyline(target, extra_top_pts, close=False, layer="Rebar")

    # -----------------------------------------------------------------------
    # 5. Distribution Reinforcement (Transverse Dots Aligned with Waist)
    # -----------------------------------------------------------------------
    dot_dia = 10.0 if is_metric else 0.4
    v_off = (cover + main_dia / 2.0 + dist_dia / 2.0) / math.cos(theta) if math.cos(theta) > 0 else cover + 10.0

    # Bottom landing distribution dots
    n_c1 = max(2, int(d1 / dist_spacing))
    for i in range(n_c1):
        cx = ox + beam_left_w / 2.0 + cover + i * dist_spacing
        if cx < ox + d1:
            draw_rebar_circle(target, (cx, oy - cover - dot_dia / 2.0), diameter=dot_dia, layer="Rebar_hatch")
            draw_rebar_circle(target, (cx, oy - waist + cover + dot_dia / 2.0), diameter=dot_dia, layer="Rebar_hatch")

    # Sloped waist distribution dots (aligned parallel to waist slab slope)
    b2_start = (ox + d1 + waist * math.sin(theta), oy - waist * math.cos(theta))
    t2_start = (ox + d1, oy)

    flight_slope_len = math.sqrt(going**2 + (height - riser)**2)
    n_c2 = max(3, int(flight_slope_len / dist_spacing))
    dx = dist_spacing * math.cos(theta)
    dy = dist_spacing * math.sin(theta)

    for i in range(n_c2 + 1):
        # Bottom mat dots along waist soffit
        cx_bot = b2_start[0] + (i + 0.5) * dx
        cy_bot = b2_start[1] + (i + 0.5) * dy + v_off
        if cx_bot <= ox + grid - d2:
            draw_rebar_circle(target, (cx_bot, cy_bot), diameter=dot_dia, layer="Rebar_hatch")

        # Top mat dots near support zones (first 1/3 and last 1/3 of flight)
        if i <= n_c2 / 3 or i >= 2 * n_c2 / 3:
            cx_top = t2_start[0] + (i + 0.5) * dx
            cy_top = t2_start[1] + (i + 0.5) * dy - v_off
            if cx_top <= ox + grid - d2:
                draw_rebar_circle(target, (cx_top, cy_top), diameter=dot_dia, layer="Rebar_hatch")

    # Top landing distribution dots
    n_c3 = max(2, int(d2 / dist_spacing))
    for i in range(n_c3):
        cx = ox + grid - d2 + cover + i * dist_spacing
        if cx < ox + grid - beam_right_w / 2.0:
            draw_rebar_circle(target, (cx, oy + height - cover - dot_dia / 2.0), diameter=dot_dia, layer="Rebar_hatch")
            draw_rebar_circle(target, (cx, oy + height - waist + cover + dot_dia / 2.0), diameter=dot_dia, layer="Rebar_hatch")

    # -----------------------------------------------------------------------
    # 6. Step Nosing Bars & Nosing Stirrups
    # -----------------------------------------------------------------------
    step_idx = min(3, n_riser - 2)
    pnose_x = ox + d1 + step_idx * tread + (20.0 if is_metric else 0.8)
    pnose_y = oy + (step_idx + 1) * riser - (20.0 if is_metric else 0.8)

    cnose = draw_rebar_circle(target, (pnose_x + (8.0 if is_metric else 0.3), pnose_y - (8.0 if is_metric else 0.3)), diameter=nosing_dia, layer="Rebar_hatch")

    # Nosing binder / stirrup L-shape
    ln1_end = (pnose_x, pnose_y - riser * 1.2)
    ln2_end = (pnose_x + tread * 1.2, pnose_y)
    draw_line(target, (pnose_x, pnose_y), ln1_end, layer="Stirrup")
    draw_line(target, (pnose_x, pnose_y), ln2_end, layer="Stirrup")

    # -----------------------------------------------------------------------
    # 7. Multileader Annotations & Callouts
    # -----------------------------------------------------------------------
    drop_top = (150.0 if is_metric else 6.0)

    # Extra bar callouts (top and bottom)
    pm1 = (P_top_extra_junc[0] - Ld * 0.5 * math.cos(theta), P_top_extra_junc[1] - Ld * 0.5 * math.sin(theta))
    draw_leader(
        target,
        [
            pm1,
            (pm1[0] + (100.0 if is_metric else 4.0), pm1[1] - drop_top),
            (pm1[0] + (250.0 if is_metric else 10.0), pm1[1] - drop_top),
        ],
        text=f"Extra bar: {_format_rebar_size(main_dia, is_metric)} @ {_format_dim(main_spacing, is_metric, include_unit=is_metric)} c/c\nMaintain Ld on both sides",
        text_height=st_sz,
        layer="Text",
    )

    pm2 = (P_bot_extra_junc[0] + Ld * 0.5 * math.cos(theta), P_bot_extra_junc[1] + Ld * 0.5 * math.sin(theta))
    draw_leader(
        target,
        [
            pm2,
            (pm2[0] - (100.0 if is_metric else 4.0), pm2[1] + drop_top),
            (pm2[0] - (250.0 if is_metric else 10.0), pm2[1] + drop_top),
        ],
        text=f"Extra bar: {_format_rebar_size(main_dia, is_metric)} @ {_format_dim(main_spacing, is_metric, include_unit=is_metric)} c/c\nMaintain Ld on both sides",
        text_height=st_sz,
        layer="Text",
    )

    # Main bar callout
    pm3 = (ox + d1 + 0.45 * going, oy + 0.45 * (height - riser) - waist * 0.3)
    draw_leader(
        target,
        [
            pm3,
            (pm3[0] + (150.0 if is_metric else 6.0), pm3[1] - drop_top),
            (pm3[0] + (300.0 if is_metric else 12.0), pm3[1] - drop_top),
        ],
        text=f"Main bar:\n{_format_rebar_size(main_dia, is_metric)} @ {_format_dim(main_spacing, is_metric, include_unit=is_metric)} c/c",
        text_height=st_sz,
        layer="Text",
    )

    # Distribution bar callout
    pm4 = (ox + d1 + 0.3 * going, oy + 0.3 * (height - riser) + waist * 0.3)
    draw_leader(
        target,
        [
            pm4,
            (pm4[0] - (150.0 if is_metric else 6.0), pm4[1] + drop_top),
            (pm4[0] - (300.0 if is_metric else 12.0), pm4[1] + drop_top),
        ],
        text=f"Distribution bar:\n{_format_rebar_size(dist_dia, is_metric)} @ {_format_dim(dist_spacing, is_metric, include_unit=is_metric)} c/c",
        text_height=st_sz,
        layer="Text",
    )

    # Support Beam Callouts
    b1_label = "Landing Beam" if beam_left_h < beam_right_h else "Main Beam"
    b2_label = "Main Beam" if beam_left_h < beam_right_h else "Landing Beam"

    draw_leader(
        target,
        [
            (ox - beam_left_w / 2.0 + (30.0 if is_metric else 1.2), oy - beam_left_h / 2.0),
            (ox - (200.0 if is_metric else 8.0), oy - beam_left_h / 2.0 - drop_top),
            (ox - (400.0 if is_metric else 16.0), oy - beam_left_h / 2.0 - drop_top),
        ],
        text=f"{b1_label}\n{_format_dim(beam_left_w, is_metric)} x {_format_dim(beam_left_h, is_metric, include_unit=is_metric)}",
        text_height=st_sz,
        layer="Text",
    )

    draw_leader(
        target,
        [
            (ox + grid + beam_right_w / 2.0 - (30.0 if is_metric else 1.2), oy + height - beam_right_h / 2.0),
            (ox + grid + (200.0 if is_metric else 8.0), oy + height - beam_right_h / 2.0 + drop_top),
            (ox + grid + (400.0 if is_metric else 16.0), oy + height - beam_right_h / 2.0 + drop_top),
        ],
        text=f"{b2_label}\n{_format_dim(beam_right_w, is_metric)} x {_format_dim(beam_right_h, is_metric, include_unit=is_metric)}",
        text_height=st_sz,
        layer="Text",
    )

    # Nosing bar & stirrup callouts
    draw_leader(
        target,
        [
            (pnose_x, pnose_y),
            (pnose_x - (150.0 if is_metric else 6.0), pnose_y + (150.0 if is_metric else 6.0)),
            (pnose_x - (300.0 if is_metric else 12.0), pnose_y + (150.0 if is_metric else 6.0)),
        ],
        text=f"{_format_rebar_size(nosing_dia, is_metric)} Nosing Bar\nin each step",
        text_height=st_sz,
        layer="Text",
    )

    # -----------------------------------------------------------------------
    # 8. Title Block (Centered Multi-line Text)
    # -----------------------------------------------------------------------
    title_cx = ox + grid / 2.0
    title_y = oy - ext_bot - (250.0 if is_metric else 10.0)

    t1_str = f"{stair.name} SECTION A-A"
    draw_text(
        target,
        t1_str,
        position=(title_cx - len(t1_str) * text_sz * 0.28, title_y),
        height=text_sz * 1.2,
        layer="Text",
    )

    t2_str = f"Waist slab thickness = {_format_dim(waist, is_metric, include_unit=True)}"
    draw_text(
        target,
        t2_str,
        position=(title_cx - len(t2_str) * text_sz * 0.25, title_y - text_sz * 1.8),
        height=text_sz,
        layer="Text",
    )

    # -----------------------------------------------------------------------
    # 9. Dimensions
    # -----------------------------------------------------------------------
    dim_y_bot = oy - (400.0 if is_metric else 16.0)

    # Horizontal landing and going dimensions
    draw_dimension(target, (ox, dim_y_bot), (ox + d1, dim_y_bot), location=(ox + d1 / 2.0, dim_y_bot - (50.0 if is_metric else 2.0)), layer="Dimension")
    draw_dimension(target, (ox + d1, dim_y_bot), (ox + d1 + going, dim_y_bot), location=(ox + d1 + going / 2.0, dim_y_bot - (50.0 if is_metric else 2.0)), layer="Dimension")
    draw_dimension(target, (ox + d1 + going, dim_y_bot), (ox + grid, dim_y_bot), location=(ox + d1 + going + d2 / 2.0, dim_y_bot - (50.0 if is_metric else 2.0)), layer="Dimension")

    # Overall grid dimension
    dim_y_tot = dim_y_bot - (250.0 if is_metric else 10.0)
    draw_dimension(target, (ox, dim_y_tot), (ox + grid, dim_y_tot), location=(ox + grid / 2.0, dim_y_tot - (50.0 if is_metric else 2.0)), layer="Dimension")

    # Step riser and tread dimensions
    step_d_x = ox + d1 + tread
    step_d_y = oy + riser
    draw_dimension(target, (step_d_x, step_d_y), (step_d_x, step_d_y + riser), location=(step_d_x + (150.0 if is_metric else 6.0), step_d_y + riser / 2.0), layer="Dimension")
    draw_dimension(target, (step_d_x, step_d_y + riser), (step_d_x + tread, step_d_y + riser), location=(step_d_x + tread / 2.0, step_d_y + riser + (100.0 if is_metric else 4.0)), layer="Dimension")

    refs.update({"section_origin": (ox, oy), "grid_span": grid, "flight_height": height})
    return refs


def plan_view(
    target: Any,
    stair: StaircaseData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
    scale: Any | None = None,
    unit: Any | None = None,
) -> dict[str, Any]:
    """Draw a staircase plan view (showing two flights with continuous UP walkline).

    Parameters
    ----------
    target
        DXF modelspace or drawing target.
    stair
        :class:`StaircaseData` object.
    origin
        (x, y) offset for the view.
    title
        Optional view title override.
    """
    ox, oy = origin
    scale = scale or getattr(stair, "scale", None)
    unit = unit or getattr(stair, "unit", None)
    is_metric = unit.is_metric if unit is not None else stair.is_metric

    flight_w = stair.flight_width_in
    tread = stair.tread_depth_in
    n_riser = max(2, stair.num_risers)
    going = (n_riser - 1) * tread
    d1 = stair.bottom_landing_depth_in
    d2 = stair.top_landing_depth_in
    well_gap = 150.0 if is_metric else 6.0

    total_w = 2 * flight_w + well_gap
    total_l = d1 + going + d2

    st_sz = 80.0 if is_metric else 3.5
    text_sz = 120.0 if is_metric else 5.0

    refs: dict[str, Any] = {"origin": (ox, oy)}

    # 1. Outer Stairwell Box
    draw_rectangle(target, origin=(ox, oy), width=total_l, height=total_w, layer="CONC_OUTLINE")

    # Flight 1 (Bottom) and Flight 2 (Top) boundaries
    y_fl1_bot = oy
    y_fl1_top = oy + flight_w

    y_fl2_bot = oy + flight_w + well_gap
    y_fl2_top = oy + total_w

    x_d1 = ox + d1
    x_d2 = ox + d1 + going

    draw_line(target, (x_d1, y_fl1_bot), (x_d1, y_fl1_top), layer="CONC_OUTLINE")
    draw_line(target, (x_d2, y_fl1_bot), (x_d2, y_fl1_top), layer="CONC_OUTLINE")

    draw_line(target, (x_d1, y_fl2_bot), (x_d1, y_fl2_top), layer="CONC_OUTLINE")
    draw_line(target, (x_d2, y_fl2_bot), (x_d2, y_fl2_top), layer="CONC_OUTLINE")

    # Center well gap lines
    draw_line(target, (x_d1, y_fl1_top), (x_d2, y_fl1_top), layer="CONC_OUTLINE")
    draw_line(target, (x_d1, y_fl2_bot), (x_d2, y_fl2_bot), layer="CONC_OUTLINE")

    # 2. Tread lines for both flights
    for i in range(1, n_riser - 1):
        tx = x_d1 + i * tread
        draw_line(target, (tx, y_fl1_bot), (tx, y_fl1_top), layer="CONC_OUTLINE")
        draw_line(target, (tx, y_fl2_bot), (tx, y_fl2_top), layer="CONC_OUTLINE")

    # 3. Break lines on stairs
    mid_x = x_d1 + going * 0.5
    draw_break_line(target, p1=(mid_x, y_fl1_bot), p2=(mid_x, y_fl1_top), layer="BREAK_LINE")
    draw_break_line(target, p1=(mid_x, y_fl2_bot), p2=(mid_x, y_fl2_top), layer="BREAK_LINE")

    # 4. Continuous Single-Polyline UP Walkline Across Flights & Landings
    y_f1_center = y_fl1_bot + flight_w * 0.5
    y_f2_center = y_fl2_bot + flight_w * 0.5

    p_start = (ox + d1 * 0.5, y_f1_center)
    p_turn1 = (ox + d1 + going + d2 * 0.5, y_f1_center)
    p_turn2 = (ox + d1 + going + d2 * 0.5, y_f2_center)
    p_end = (ox + d1 * 0.5, y_f2_center)

    # Continuous walkline polyline
    draw_polyline(target, [p_start, p_turn1, p_turn2, p_end], close=False, layer="REBAR")

    # Start dot
    draw_circle(target, p_start, radius=(25.0 if is_metric else 1.0), layer="REBAR")

    # End Arrowhead at top landing (pointing left)
    arr_sz = 60.0 if is_metric else 2.5
    arr_pts = [
        (p_end[0] + arr_sz, p_end[1] + arr_sz * 0.4),
        p_end,
        (p_end[0] + arr_sz, p_end[1] - arr_sz * 0.4),
    ]
    draw_polyline(target, arr_pts, close=True, layer="REBAR")

    # "UP" Text near start
    draw_text(target, "UP", position=(p_start[0] + (100.0 if is_metric else 4.0), y_f1_center + (40.0 if is_metric else 1.5)), height=st_sz, layer="Text")

    # 5. Section Cut Line A-A across plan
    sec_y = y_fl1_bot + flight_w * 0.15
    sec_x1 = ox - (250.0 if is_metric else 10.0)
    sec_x2 = ox + total_l + (250.0 if is_metric else 10.0)
    draw_line(target, (sec_x1, sec_y), (sec_x2, sec_y), layer="SECTION")
    draw_section_cut_symbol(target, center=(sec_x1, sec_y), letter="A", size=st_sz * 1.2, layer="SECTION")
    draw_section_cut_symbol(target, center=(sec_x2, sec_y), letter="A", size=st_sz * 1.2, layer="SECTION")

    # 6. Dimensions
    dim_y = oy - (300.0 if is_metric else 12.0)
    draw_dimension(target, (ox, dim_y), (x_d1, dim_y), location=(ox + d1 / 2.0, dim_y - (50.0 if is_metric else 2.0)), layer="Dimension")
    draw_dimension(target, (x_d1, dim_y), (x_d2, dim_y), location=(x_d1 + going / 2.0, dim_y - (50.0 if is_metric else 2.0)), layer="Dimension")
    draw_dimension(target, (x_d2, dim_y), (ox + total_l, dim_y), location=(x_d2 + d2 / 2.0, dim_y - (50.0 if is_metric else 2.0)), layer="Dimension")

    dim_x = ox - (300.0 if is_metric else 12.0)
    draw_dimension(target, (dim_x, oy), (dim_x, oy + flight_w), location=(dim_x - (50.0 if is_metric else 2.0), oy + flight_w / 2.0), layer="Dimension")
    draw_dimension(target, (dim_x, oy + flight_w + well_gap), (dim_x, oy + total_w), location=(dim_x - (50.0 if is_metric else 2.0), oy + flight_w + well_gap + flight_w / 2.0), layer="Dimension")

    # 7. Title Block (Centered at Bottom of Plan)
    plan_title_str = title if title is not None else f"{stair.name} - STAIRCASE PLAN"
    plan_cx = ox + total_l / 2.0
    plan_y = oy - (500.0 if is_metric else 20.0)
    draw_text(
        target,
        plan_title_str,
        position=(plan_cx - len(plan_title_str) * text_sz * 0.28, plan_y),
        height=text_sz * 1.2,
        layer="Text",
    )

    refs.update({"plan_origin": (ox, oy), "total_width": total_w, "total_length": total_l})
    return refs


__all__ = ["plan_view", "section_view"]

