"""struct_draw.elements.beam_profile — Longitudinal profile + cross-section views for multi-span continuous beams.

This module implements detailed, production-ready structural drawing functions
for multi-span continuous beams based on the reference standard in
``references/beam_profile.py``.

Key features:
* Multi-span longitudinal elevation (L-Section) across grid lines & columns.
* Column stubs at supports with top/bottom break lines.
* Grid line centerlines with numbered/lettered grid bubbles.
* Complete reinforcement detailing:
  - Continuous top & bottom main longitudinal bars with end anchorage hooks into terminal columns.
  - Top support extra bars (negative reinforcement / cranked bars) over column supports extending 0.25 * L_span into adjacent spans.
  - Stirrup zones with closer spacing at supports (0.25 * L_span) and wider spacing at mid-span.
* Dimension chains:
  - Stirrup specification callouts (e.g. "10mm dia @ 100 mm c/c", "10mm dia @ 150 mm c/c").
  - Zone length dimensions (support zone, mid-span zone).
  - Center-to-center span dimensions and column width dimensions.
  - Overall continuous beam length dimension.
* Section cut indicators (Section 1-1 at support, Section 2-2 at mid-span).
* Plinth / Floor Level (PL / FFL) marker.
* Companion cross-sections (Section 1-1 & Section 2-2) with stirrups, hooks, and rebar dots.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

from struct_draw.core.composite import (
    draw_break_line,
    draw_dimension,
    draw_level_marker,
    draw_line,
    draw_polyline,
    draw_rebar_circle,
    draw_section_cut_symbol,
    draw_stirrup_hooked,
    draw_text,
)
from struct_draw.core.data import BeamProfileData, Rebar
from struct_draw.core.primitives import draw_circle, draw_mtext, draw_rectangle
from struct_draw.core.units import DrawingScale, DrawingUnit
from struct_draw.style.annotation_config import AnnotationConfig, DEFAULT_ANNOTATION_CONFIG


def _clean_text(txt: str) -> str:
    """Replace non-rendering unicode symbols with standard CAD text."""
    if not txt:
        return ""
    return txt.replace("φ", "mm dia").replace("Φ", "mm dia").replace("ϕ", "mm dia")


def _format_dim(val: float, is_metric: bool = False, include_unit: bool = False) -> str:
    """Format dimension value string."""
    if is_metric or val >= 300.0:
        if include_unit:
            return f"{int(val)}mm" if val.is_integer() else f"{val:.1f}mm"
        return f"{int(val)}" if val.is_integer() else f"{val:.1f}"
    if val.is_integer():
        return f'{int(val)}"'
    return f'{val:.1f}"'


def _format_rebar_spec(
    bar_size: str, spacing: float, is_metric: bool = False
) -> str:
    """Format stirrup specification string for dimension overrides."""
    clean_size = _clean_text(bar_size) if bar_size else ("10mm dia" if is_metric else "#3")
    sp_str = _format_dim(spacing, is_metric=is_metric, include_unit=is_metric)
    unit_suffix = "c/c" if is_metric else '" c/c'
    return f"{clean_size} @ {sp_str}{unit_suffix}"


def profile_view(
    target: Any,
    beam_profile: BeamProfileData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
    scale: Any = None,
    unit: Any = None,
) -> dict[str, Any]:
    """Draw a multi-span continuous beam longitudinal elevation (L-Section).

    The view includes:
    * Grid centerlines and grid bubble callouts.
    * Column support stubs with top and bottom break lines.
    * Beam concrete outline.
    * Continuous top and bottom longitudinal rebar with 90° hooks into end columns.
    * Top extra negative rebar over interior supports (extending 0.25 * span).
    * Stirrup zones (dense near supports, wider at mid-span).
    * Dimension chains (stirrup specs, zone lengths, span C/C, total length).
    * Section callout symbols (Section 1-1 at support, Section 2-2 at midspan).
    * Level marker (PL/FFL).
    * Drawing title.

    Returns a metadata dictionary containing key geometry and drawn bounds.
    """
    ox, oy = origin
    is_metric = beam_profile.is_metric

    spans = list(beam_profile.spans_in) if beam_profile.spans_in else [216.0, 180.0, 216.0]
    n_spans = len(spans)
    col = beam_profile.col_width_in
    beam_depth = beam_profile.beam_depth_in
    cover = beam_profile.cover_in
    ext = beam_profile.col_extension_in
    grid_ext = beam_profile.grid_extension_in

    total_len = sum(spans)

    # Calculate cumulative grid line X coordinates
    grid_x: list[float] = [ox]
    curr_x = ox
    for s in spans:
        curr_x += s
        grid_x.append(curr_x)

    refs: dict[str, Any] = {
        "origin": (ox, oy),
        "spans": spans,
        "total_length": total_len,
        "grid_x": grid_x,
    }

    # Vertical reference levels
    y_col_bot = oy
    y_beam_bot = oy + ext
    y_beam_top = oy + ext + beam_depth
    y_col_top = oy + 2.0 * ext + beam_depth
    y_grid_bubble = y_col_top + grid_ext

    # Layer names
    lay_beam = "BEAM"
    lay_col = "COLUMN"
    lay_rebar = "REBAR"
    lay_stirrup = "STIRRUP"
    lay_dim = "DIM_LINEAR"
    lay_cen = "CEN"
    lay_text = "TEXT"
    lay_break = "BREAK_LINE"

    # Scale-dependent graphical parameters
    active_scale = scale or getattr(beam_profile, "scale", None)
    active_unit = unit or getattr(beam_profile, "unit", None)
    ann = DEFAULT_ANNOTATION_CONFIG
    if active_scale is not None or active_unit is not None:
        text_size = ann.text_height(active_scale, active_unit)
        title_size = ann.title_height(active_scale, active_unit)
        bubble_rad = ann.bubble_radius(active_scale, active_unit)
        dim_layer_gap = ann.dim_offset(active_scale, active_unit)
        jog = text_size * 0.75
    else:
        text_size = 150.0 if is_metric else 6.0
        title_size = 250.0 if is_metric else 10.0
        bubble_rad = 250.0 if is_metric else 12.0
        dim_layer_gap = 300.0 if is_metric else 12.0
        jog = 150.0 if is_metric else 6.0

    # 1. Grid Centerlines & Grid Bubbles
    grid_labels = list(beam_profile.grid_labels) if beam_profile.grid_labels else []
    for idx, gx in enumerate(grid_x):
        # Centerline
        draw_line(target, (gx, y_col_bot - grid_ext * 0.5), (gx, y_grid_bubble), layer=lay_cen)
        # Grid Bubble
        draw_circle(target, (gx, y_grid_bubble + bubble_rad), radius=bubble_rad, layer=lay_dim)
        # Label text inside bubble (display clean single mark, e.g. 'A', '1')
        raw_label = grid_labels[idx] if idx < len(grid_labels) else (chr(65 + idx) if idx < 26 else f"G{idx+1}")
        clean_lbl = raw_label
        if clean_lbl.upper().startswith("GRID "):
            clean_lbl = clean_lbl[5:].strip()
        draw_text(
            target,
            clean_lbl,
            position=(gx, y_grid_bubble + bubble_rad),
            height=text_size,
            align="middle_center",
            layer=lay_text,
        )

    # 2. Columns and Break Lines
    for idx, gx in enumerate(grid_x):
        x_left = gx - col / 2.0
        x_right = gx + col / 2.0

        # Column break line polyline points relative to column center gx
        break_pts = [
            (x_left - jog, 0.0),
            (gx - jog * 0.5, 0.0),
            (gx, jog),
            (gx, -jog),
            (gx + jog * 0.5, 0.0),
            (x_right + jog, 0.0),
        ]

        # Lower break line
        draw_polyline(target, [(px, py + y_col_bot) for px, py in break_pts], layer=lay_break)
        # Upper break line
        draw_polyline(target, [(px, py + y_col_top) for px, py in break_pts], layer=lay_break)

        # Column vertical edges
        if idx == 0:
            # Left end column: outer left face continuous, inner right face split
            draw_line(target, (x_left, y_col_bot), (x_left, y_col_top), layer=lay_col)
            draw_line(target, (x_right, y_col_bot), (x_right, y_beam_bot), layer=lay_col)
            draw_line(target, (x_right, y_beam_top), (x_right, y_col_top), layer=lay_col)
        elif idx == len(grid_x) - 1:
            # Right end column: outer right face continuous, inner left face split
            draw_line(target, (x_right, y_col_bot), (x_right, y_col_top), layer=lay_col)
            draw_line(target, (x_left, y_col_bot), (x_left, y_beam_bot), layer=lay_col)
            draw_line(target, (x_left, y_beam_top), (x_left, y_col_top), layer=lay_col)
        else:
            # Interior column: both inner faces split at beam height
            draw_line(target, (x_left, y_col_bot), (x_left, y_beam_bot), layer=lay_col)
            draw_line(target, (x_right, y_col_bot), (x_right, y_beam_bot), layer=lay_col)
            draw_line(target, (x_left, y_beam_top), (x_left, y_col_top), layer=lay_col)
            draw_line(target, (x_right, y_beam_top), (x_right, y_col_top), layer=lay_col)

        # Column width dimension
        draw_dimension(
            target,
            (x_left, y_col_bot),
            (x_right, y_col_bot),
            location=(gx, y_col_bot - dim_layer_gap * 0.8),
            text_override=_format_dim(col, is_metric=is_metric),
            layer=lay_dim,
        )

    # 3. Beam Concrete Outline (Horizontal top and bottom edges across spans)
    for i in range(n_spans):
        x_start = grid_x[i] + col / 2.0
        x_end = grid_x[i + 1] - col / 2.0
        # Bottom edge
        draw_line(target, (x_start, y_beam_bot), (x_end, y_beam_bot), layer=lay_beam)
        # Top edge
        draw_line(target, (x_start, y_beam_top), (x_end, y_beam_top), layer=lay_beam)

    # 4. Continuous Longitudinal Reinforcement
    y_rebar_top = y_beam_top - cover
    y_rebar_bot = y_beam_bot + cover
    hook_len = max(cover * 2.0, beam_depth * 0.5)

    # Top continuous bar with 90° hooks in end columns
    x_left_end = grid_x[0] - col / 2.0 + cover
    x_right_end = grid_x[-1] + col / 2.0 - cover
    top_bar_pts = [
        (x_left_end, y_rebar_top - hook_len),
        (x_left_end, y_rebar_top),
        (x_right_end, y_rebar_top),
        (x_right_end, y_rebar_top - hook_len),
    ]
    draw_polyline(target, top_bar_pts, close=False, layer=lay_rebar)

    # Bottom continuous bar with 90° hooks in end columns
    x_left_bot = x_left_end + (20.0 if is_metric else 0.75)
    x_right_bot = x_right_end - (20.0 if is_metric else 0.75)
    bot_bar_pts = [
        (x_left_bot, y_rebar_bot + hook_len),
        (x_left_bot, y_rebar_bot),
        (x_right_bot, y_rebar_bot),
        (x_right_bot, y_rebar_bot + hook_len),
    ]
    draw_polyline(target, bot_bar_pts, close=False, layer=lay_rebar)

    # 5. Top Support Extra / Cranked Rebar (Over All Column Supports)
    supp_spacing = beam_profile.support_stirrup_spacing_in
    mid_spacing = beam_profile.mid_stirrup_spacing_in
    st_size = beam_profile.stirrup.size if beam_profile.stirrup else ("10mm dia" if is_metric else "#3")

    crank_step = 50.0 if is_metric else 2.0
    y_extra = y_rebar_top - (15.0 if is_metric else 0.5)

    # Draw extra top negative reinforcement over every support column
    for supp_idx in range(n_spans + 1):
        gx_supp = grid_x[supp_idx]
        if supp_idx == 0:
            # Leftmost terminal support column
            raw_s = 0.25 * spans[0]
            s_len = math.ceil(raw_s / 50.0) * 50.0 if is_metric else math.ceil(raw_s / 2.0) * 2.0
            x_col_hook = gx_supp - col / 2.0 + cover + (15.0 if is_metric else 0.5)
            x_span_ext = gx_supp + col / 2.0 + s_len
            x_crank = x_span_ext + crank_step
            extra_pts = [
                (x_col_hook, y_extra - hook_len),
                (x_col_hook, y_extra),
                (x_span_ext, y_extra),
                (x_crank, y_extra - crank_step),
            ]
            draw_polyline(target, extra_pts, close=False, layer=lay_rebar)

        elif supp_idx == n_spans:
            # Rightmost terminal support column
            raw_s = 0.25 * spans[-1]
            s_len = math.ceil(raw_s / 50.0) * 50.0 if is_metric else math.ceil(raw_s / 2.0) * 2.0
            x_col_hook = gx_supp + col / 2.0 - cover - (15.0 if is_metric else 0.5)
            x_span_ext = gx_supp - col / 2.0 - s_len
            x_crank = x_span_ext - crank_step
            extra_pts = [
                (x_crank, y_extra - crank_step),
                (x_span_ext, y_extra),
                (x_col_hook, y_extra),
                (x_col_hook, y_extra - hook_len),
            ]
            draw_polyline(target, extra_pts, close=False, layer=lay_rebar)

        else:
            # Intermediate interior support column
            raw_s_left = 0.25 * spans[supp_idx - 1]
            raw_s_right = 0.25 * spans[supp_idx]
            s_len_left = math.ceil(raw_s_left / 50.0) * 50.0 if is_metric else math.ceil(raw_s_left / 2.0) * 2.0
            s_len_right = math.ceil(raw_s_right / 50.0) * 50.0 if is_metric else math.ceil(raw_s_right / 2.0) * 2.0

            x_left = gx_supp - col / 2.0 - s_len_left
            x_left_crank = x_left - crank_step
            x_right = gx_supp + col / 2.0 + s_len_right
            x_right_crank = x_right + crank_step

            extra_pts = [
                (x_left_crank, y_extra - crank_step),
                (x_left, y_extra),
                (x_right, y_extra),
                (x_right_crank, y_extra - crank_step),
            ]
            draw_polyline(target, extra_pts, close=False, layer=lay_rebar)

    # Stirrups, Dimensions & Section Cut Lines per span
    for i, span in enumerate(spans):
        gx_start = grid_x[i]
        gx_end = grid_x[i + 1]

        # Calculate support zone length = 0.25 * span (rounded to 50 mm / 2 in)
        raw_supp = 0.25 * span
        if is_metric:
            supp_len = math.ceil(raw_supp / 50.0) * 50.0
        else:
            supp_len = math.ceil(raw_supp / 2.0) * 2.0

        mid_len = max(0.0, span - 2.0 * supp_len - col)

        # Stirrups in elevation
        x_span_start = gx_start + col / 2.0
        x_span_end = gx_end - col / 2.0

        # Draw representative stirrup vertical lines in profile
        # Left support zone
        cur_x = x_span_start + supp_spacing
        while cur_x < x_span_start + supp_len:
            draw_line(target, (cur_x, y_beam_bot + cover * 0.5), (cur_x, y_beam_top - cover * 0.5), layer=lay_stirrup)
            cur_x += supp_spacing

        # Mid span zone
        cur_x = x_span_start + supp_len + mid_spacing
        while cur_x < x_span_end - supp_len:
            draw_line(target, (cur_x, y_beam_bot + cover * 0.5), (cur_x, y_beam_top - cover * 0.5), layer=lay_stirrup)
            cur_x += mid_spacing

        # Right support zone
        cur_x = x_span_end - supp_len + supp_spacing
        while cur_x < x_span_end:
            draw_line(target, (cur_x, y_beam_bot + cover * 0.5), (cur_x, y_beam_top - cover * 0.5), layer=lay_stirrup)
            cur_x += supp_spacing

        # Dimensions under span
        # Layer 1: Stirrup Specification Callouts
        p_s1_start = (x_span_start, y_col_bot)
        p_s1_end = (x_span_start + supp_len, y_col_bot)
        draw_dimension(
            target,
            p_s1_start,
            p_s1_end,
            location=((x_span_start + supp_len / 2.0), y_col_bot - dim_layer_gap * 1.5),
            text_override=_format_rebar_spec(st_size, supp_spacing, is_metric=is_metric),
            layer=lay_dim,
        )

        p_m_start = (x_span_start + supp_len, y_col_bot)
        p_m_end = (x_span_end - supp_len, y_col_bot)
        draw_dimension(
            target,
            p_m_start,
            p_m_end,
            location=((x_span_start + supp_len + mid_len / 2.0), y_col_bot - dim_layer_gap * 1.5),
            text_override=_format_rebar_spec(st_size, mid_spacing, is_metric=is_metric),
            layer=lay_dim,
        )

        p_s2_start = (x_span_end - supp_len, y_col_bot)
        p_s2_end = (x_span_end, y_col_bot)
        draw_dimension(
            target,
            p_s2_start,
            p_s2_end,
            location=((x_span_end - supp_len / 2.0), y_col_bot - dim_layer_gap * 1.5),
            text_override=_format_rebar_spec(st_size, supp_spacing, is_metric=is_metric),
            layer=lay_dim,
        )

        # Layer 2: Zone Length Dimensions
        draw_dimension(
            target,
            p_s1_start,
            p_s1_end,
            location=((x_span_start + supp_len / 2.0), y_col_bot - dim_layer_gap * 2.3),
            text_override=_format_dim(supp_len, is_metric=is_metric),
            layer=lay_dim,
        )
        draw_dimension(
            target,
            p_m_start,
            p_m_end,
            location=((x_span_start + supp_len + mid_len / 2.0), y_col_bot - dim_layer_gap * 2.3),
            text_override=_format_dim(mid_len, is_metric=is_metric),
            layer=lay_dim,
        )
        draw_dimension(
            target,
            p_s2_start,
            p_s2_end,
            location=((x_span_end - supp_len / 2.0), y_col_bot - dim_layer_gap * 2.3),
            text_override=_format_dim(supp_len, is_metric=is_metric),
            layer=lay_dim,
        )

        # Layer 3: Center-to-Center Span Dimension
        draw_dimension(
            target,
            (gx_start, y_col_bot),
            (gx_end, y_col_bot),
            location=((gx_start + span / 2.0), y_col_bot - dim_layer_gap * 3.1),
            text_override=_format_dim(span, is_metric=is_metric, include_unit=False),
            layer=lay_dim,
        )

        # Section Callout Markers & Vertical Section Cut Lines
        sec1_left_x = x_span_start + supp_len / 2.0
        sec2_mid_x = x_span_start + supp_len + mid_len / 2.0
        sec1_right_x = x_span_end - supp_len / 2.0

        y_sec_line_bot = y_beam_bot - (100.0 if is_metric else 4.0)
        y_sec_line_top = y_beam_top + (150.0 if is_metric else 6.0)
        bubble_center_y = y_sec_line_top + (80.0 if is_metric else 3.0)

        for sec_x, sec_label in [
            (sec1_left_x, "1"),
            (sec2_mid_x, "2"),
            (sec1_right_x, "1"),
        ]:
            # Draw vertical section line passing through beam
            draw_line(
                target,
                (sec_x, y_sec_line_bot),
                (sec_x, y_sec_line_top),
                layer=lay_dim,
            )
            # Draw section cut circle callout symbol
            draw_section_cut_symbol(
                target,
                center=(sec_x, bubble_center_y),
                letter=sec_label,
                size=(100.0 if is_metric else 4.0),
                layer=lay_dim,
            )

    # Overall Beam Length Dimension (Layer 4 below)
    draw_dimension(
        target,
        (grid_x[0], y_col_bot),
        (grid_x[-1], y_col_bot),
        location=((ox + total_len / 2.0), y_col_bot - dim_layer_gap * 4.0),
        text_override=f"TOTAL C/C = {_format_dim(total_len, is_metric=is_metric, include_unit=False)}",
        layer=lay_dim,
    )

    # 6. Level Indicator (e.g., PL+3.0 m)
    level_x = grid_x[-1] + col / 2.0
    draw_level_marker(
        target,
        anchor=(level_x, y_beam_top),
        direction="right",
        length=(1400.0 if is_metric else 50.0),
        label=beam_profile.level_text,
        label_offset=(300.0 if is_metric else 12.0, 50.0 if is_metric else 2.0),
        text_height=text_size,
        line_layer=lay_dim,
        text_layer=lay_text,
    )

    # 7. Main Drawing Title MText (generous width prevents wrapping to multiple lines)
    title_text = title or beam_profile.name or "L-SECTION OF BEAM ALONG GRIDS A-A"
    t_half_len = len(title_text) * title_size * 0.30
    draw_mtext(
        target,
        title_text,
        position=(ox + total_len / 2.0 - t_half_len, y_col_bot - dim_layer_gap * 5.0),
        width=(25000.0 if is_metric else 1000.0),
        height=title_size,
        layer=lay_text,
    )

    return refs


def section_views(
    target: Any,
    beam_profile: BeamProfileData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
    scale: Any = None,
    unit: Any = None,
) -> dict[str, Any]:
    """Draw cross-section views (Section 1-1 at Support and Section 2-2 at Mid-Span).

    Shows concrete rectangle, stirrup with parallel 135° seismic hooks,
    longitudinal rebar dots, linear width and depth dimensions, and section titles.
    """
    ox, oy = origin
    is_metric = beam_profile.is_metric
    w = beam_profile.beam_width_in
    d = beam_profile.beam_depth_in
    cover = beam_profile.cover_in

    lay_beam = "BEAM"
    lay_stirrup = "STIRRUP"
    lay_rebar = "REBAR_HATCH"
    lay_dim = "DIM_LINEAR"
    lay_text = "TEXT"

    active_scale = scale or getattr(beam_profile, "scale", None)
    active_unit = unit or getattr(beam_profile, "unit", None)
    ann = DEFAULT_ANNOTATION_CONFIG
    if active_scale is not None or active_unit is not None:
        text_size = ann.text_height(active_scale, active_unit)
        dim_gap = ann.dim_offset(active_scale, active_unit)
    else:
        text_size = 125.0 if is_metric else 5.0
        dim_gap = 150.0 if is_metric else 6.0
    dot_dia = 20.0 if is_metric else 0.75
    section_spacing = max(w * 3.0, w + (2600.0 if is_metric else 100.0))

    # ----- Section 1-1: Support Section (With Top Extra Bars) -----
    ox1 = ox
    oy1 = oy

    # Outer concrete outline
    draw_rectangle(target, origin=(ox1, oy1), width=w, height=d, close=True, layer=lay_beam)

    # Stirrup (Double-line)
    st_w = max(1.0, w - 2.0 * cover)
    st_h = max(1.0, d - 2.0 * cover)
    tie_size = getattr(beam_profile.stirrup, "size", "10mm dia") or "10mm dia"
    tie_dia = 10.0 if is_metric else 0.375
    if "12" in tie_size:
        tie_dia = 12.0 if is_metric else 0.5
    elif "8" in tie_size:
        tie_dia = 8.0 if is_metric else 0.25

    draw_stirrup_hooked(
        target,
        width=st_w,
        height=st_h,
        origin=(ox1 + cover, oy1 + cover),
        tie_diameter=tie_dia,
        hook_length=(75.0 if is_metric else 3.0),
        corner="top_left",
        double_line=True,
        layer=lay_stirrup,
    )

    # Rebar dots: 4 top bars (support region negative steel), 3 bottom bars
    top_y = oy1 + d - cover - tie_dia - dot_dia / 2.0
    bot_y = oy1 + cover + tie_dia + dot_dia / 2.0

    # Top bars (4 dots)
    x_step_top = (w - 2.0 * cover - 2.0 * tie_dia - dot_dia) / 3.0
    for k in range(4):
        cx = ox1 + cover + tie_dia + dot_dia / 2.0 + k * x_step_top
        draw_rebar_circle(target, (cx, top_y), diameter=dot_dia, layer=lay_rebar)

    # Bottom bars (3 dots)
    x_step_bot = (w - 2.0 * cover - 2.0 * tie_dia - dot_dia) / 2.0
    for k in range(3):
        cx = ox1 + cover + tie_dia + dot_dia / 2.0 + k * x_step_bot
        draw_rebar_circle(target, (cx, bot_y), diameter=dot_dia, layer=lay_rebar)

    # Dimensions
    draw_dimension(
        target,
        (ox1, oy1),
        (ox1 + w, oy1),
        location=(ox1 + w / 2.0, oy1 - dim_gap),
        text_override=_format_dim(w, is_metric=is_metric),
        layer=lay_dim,
    )
    draw_dimension(
        target,
        (ox1, oy1),
        (ox1, oy1 + d),
        location=(ox1 - dim_gap, oy1 + d / 2.0),
        text_override=_format_dim(d, is_metric=is_metric),
        layer=lay_dim,
    )

    # Title label
    draw_text(
        target,
        "SECTION 1-1",
        position=(ox1 + w / 2.0, oy1 - dim_gap * 2.2),
        height=text_size,
        align="middle_center",
        layer=lay_text,
    )

    # ----- Section 2-2: Mid-Span Section (Continuous Bars Only) -----
    ox2 = ox + section_spacing
    oy2 = oy

    # Outer concrete outline
    draw_rectangle(target, origin=(ox2, oy2), width=w, height=d, close=True, layer=lay_beam)

    # Stirrup (Double-line)
    draw_stirrup_hooked(
        target,
        width=st_w,
        height=st_h,
        origin=(ox2 + cover, oy2 + cover),
        tie_diameter=tie_dia,
        hook_length=(75.0 if is_metric else 3.0),
        corner="top_left",
        double_line=True,
        layer=lay_stirrup,
    )

    # Top bars (2 dots at corners)
    top_y2 = oy2 + d - cover - tie_dia - dot_dia / 2.0
    bot_y2 = oy2 + cover + tie_dia + dot_dia / 2.0

    cx_left = ox2 + cover + tie_dia + dot_dia / 2.0
    cx_right = ox2 + w - cover - tie_dia - dot_dia / 2.0
    draw_rebar_circle(target, (cx_left, top_y2), diameter=dot_dia, layer=lay_rebar)
    draw_rebar_circle(target, (cx_right, top_y2), diameter=dot_dia, layer=lay_rebar)

    # Bottom bars (3 dots)
    for k in range(3):
        cx = ox2 + cover + tie_dia + dot_dia / 2.0 + k * x_step_bot
        draw_rebar_circle(target, (cx, bot_y2), diameter=dot_dia, layer=lay_rebar)

    # Dimensions
    draw_dimension(
        target,
        (ox2, oy2),
        (ox2 + w, oy2),
        location=(ox2 + w / 2.0, oy2 - dim_gap),
        text_override=_format_dim(w, is_metric=is_metric),
        layer=lay_dim,
    )
    draw_dimension(
        target,
        (ox2, oy2),
        (ox2, oy2 + d),
        location=(ox2 - dim_gap, oy2 + d / 2.0),
        text_override=_format_dim(d, is_metric=is_metric),
        layer=lay_dim,
    )

    # Title label
    draw_text(
        target,
        "SECTION 2-2",
        position=(ox2 + w / 2.0, oy2 - dim_gap * 2.2),
        height=text_size,
        align="middle_center",
        layer=lay_text,
    )

    return {
        "origin_sec1": (ox1, oy1),
        "origin_sec2": (ox2, oy2),
        "width": w,
        "depth": d,
    }


def drawing(
    target: Any,
    beam_profile: BeamProfileData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
    scale: Any = None,
    unit: Any = None,
) -> dict[str, Any]:
    """Draw the full continuous beam drawing sheet (Profile Elevation + Section Views).

    Combines the multi-span longitudinal profile (profile_view) and the
    cross-sections (section_views) arranged cleanly.
    """
    ox, oy = origin
    is_metric = beam_profile.is_metric

    # 1. Draw Profile View (Elevation)
    refs_prof = profile_view(target, beam_profile, origin=(ox, oy), title=title, scale=scale, unit=unit)

    # Position section views below or alongside the profile, centered under run
    total_len = sum(beam_profile.spans_in) if beam_profile.spans_in else 600.0
    sec_y = oy - (2500.0 if is_metric else 100.0)
    w_bm = beam_profile.beam_width_in
    spacing = max(w_bm * 3.0, w_bm + (2600.0 if is_metric else 100.0))
    sec_x = ox + (total_len - (spacing + w_bm)) / 2.0

    refs_sec = section_views(target, beam_profile, origin=(sec_x, sec_y), scale=scale, unit=unit)

    return {
        "profile": refs_prof,
        "sections": refs_sec,
    }


__all__ = ["profile_view", "section_views", "drawing"]
