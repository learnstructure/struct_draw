"""struct_draw.elements.column — Professional ACI 318 Section + Elevation views for columns.

A column section view shows:
* Concrete outer outline
* Perimeter closed hoop/stirrup wrapping perfectly on the OUTSIDE of all longitudinal rebars
* Standard 135° seismic hooks extending >= 6db into the concrete core, directly touching the corner rebar
* Longitudinal rebar circles (corners + intermediate faces) with clear cover
* Supplementary crossties / interior ties when required
* Cross-sectional dimensions and view title
* AutoCAD LEADER objects with inclined pointers, horizontal shoulders, and clean two-line text

A column elevation view follows ACI 318 seismic detailing:
* Upper and lower framing beams/slabs and joint regions
* End confinement zones (Lo = max(h, b, H/6, 18" / 450mm)) with closely spaced hoops (so)
* First hoop <= 2" (50mm) from joint faces
* Central region with typical tie spacing (s)
* Seismic lap splice in the center half of column clear height (ACI 318 §18.7.4.3) with 1:6 crank
* Hoops continuing through the beam-column joint per ACI 318 §18.8.3
* Dimension chains: Lo zones, central zone, clear height Lu, splice length Ld
* AutoCAD LEADER callouts with inclined pointer lines, landing shoulders, and clean two-line text
* Level marker lines (Level N, Beam Soffit, Level N+1)
* Professional ACI 318 seismic detailing notes

The master `drawing` function dynamically positions both the
elevation and section views side-by-side (or stacked) without
overlap, fully respecting bounding boxes and dimensions.
"""

from __future__ import annotations

import math
from typing import Any

from struct_draw.core.composite import (
    draw_break_line,
    draw_concrete_outline,
    draw_dimension,
    draw_leader,
    draw_line,
    draw_polyline,
    draw_rebar_circle,
    draw_text,
)
from struct_draw.core.data import ColumnData, Rebar
from struct_draw.core.primitives import draw_rectangle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _detect_metric(column: ColumnData) -> bool:
    """Determine whether column data is in metric units (mm) or imperial (inches)."""
    if getattr(column, "is_metric", None) is not None:
        return bool(column.is_metric)
    w = column.section.width_in
    d = column.section.depth_in
    h = column.height_in
    return w >= 100.0 or d >= 100.0 or h >= 1000.0


def _format_dim(val: float, is_metric: bool = False) -> str:
    """Format dimension string for column drawings."""
    if is_metric or val >= 300.0:
        return f"{int(val)}" if val.is_integer() else f"{val:.1f}"
    return f'{int(val)}"' if val.is_integer() else f'{val:.1f}"'


_BAR_DIA_BY_DESIGNATOR: dict[str, float] = {
    "#3": 0.375, "#4": 0.500, "#5": 0.625, "#6": 0.750,
    "#7": 0.875, "#8": 1.000, "#9": 1.128, "#10": 1.270,
    "#11": 1.410, "#14": 1.693, "#18": 2.257,
}


def _bar_diameter(size: str, is_metric: bool = False) -> float:
    if is_metric:
        digits = "".join(c for c in size if c.isdigit())
        return float(digits) if digits else 20.0
    return _BAR_DIA_BY_DESIGNATOR.get(size, 1.0)


def _corner_bar(prefix: str, idx: int) -> Rebar:
    """A placeholder longitudinal bar used for default column layouts."""
    return Rebar(mark=f"{prefix}{idx}", size="#8", quantity=1, length_in=0.0)


def _compute_rebar_coords(
    total_bars: int,
    w: float,
    d: float,
    cover: float,
    *args: float,
    tie_dia: float | None = None,
    bar_dia: float | None = None,
    **kwargs: Any,
) -> list[tuple[float, float]]:
    """Compute local (x, y) coordinates of all longitudinal bars.

    In CAD section representation, longitudinal bars sit tangent to the outer stirrup:
    x_min = cover + bar_dia / 2
    x_max = w - cover - bar_dia / 2
    y_min = cover + bar_dia / 2
    y_max = d - cover - bar_dia / 2
    """
    if bar_dia is None:
        if len(args) == 2:
            # Called as (total_bars, w, d, cover, tie_dia, bar_dia)
            tie_dia = args[0]
            bar_dia = args[1]
        elif len(args) == 1:
            # Called as (total_bars, w, d, cover, bar_dia)
            bar_dia = args[0]
        else:
            bar_dia = kwargs.get("bar_dia", 1.0)
    if tie_dia is None:
        tie_dia = kwargs.get("tie_dia", 0.0)

    r = bar_dia / 2.0
    x_min = cover + tie_dia + r
    x_max = w - cover - tie_dia - r
    y_min = cover + tie_dia + r
    y_max = d - cover - tie_dia - r

    if total_bars <= 4:
        return [
            (x_min, y_min),  # Bottom-Left
            (x_max, y_min),  # Bottom-Right
            (x_max, y_max),  # Top-Right
            (x_min, y_max),  # Top-Left
        ]

    if total_bars == 6:
        x_mid = (x_min + x_max) / 2.0
        return [
            (x_min, y_min),
            (x_mid, y_min),
            (x_max, y_min),
            (x_max, y_max),
            (x_mid, y_max),
            (x_min, y_max),
        ]

    if total_bars == 8:
        x_mid = (x_min + x_max) / 2.0
        y_mid = (y_min + y_max) / 2.0
        return [
            (x_min, y_min),
            (x_mid, y_min),
            (x_max, y_min),
            (x_max, y_mid),
            (x_max, y_max),
            (x_mid, y_max),
            (x_min, y_max),
            (x_min, y_mid),
        ]

    pts: list[tuple[float, float]] = []
    perim = 2.0 * ((x_max - x_min) + (y_max - y_min))
    for i in range(total_bars):
        dist = (perim * i / total_bars) % perim
        if dist <= (x_max - x_min):
            pts.append((x_min + dist, y_min))
        elif dist <= (x_max - x_min) + (y_max - y_min):
            d1 = dist - (x_max - x_min)
            pts.append((x_max, y_min + d1))
        elif dist <= 2.0 * (x_max - x_min) + (y_max - y_min):
            d2 = dist - ((x_max - x_min) + (y_max - y_min))
            pts.append((x_max - d2, y_max))
        else:
            d3 = dist - (2.0 * (x_max - x_min) + (y_max - y_min))
            pts.append((x_min, y_max - d3))
    return pts


# ---------------------------------------------------------------------------
# Section View
# ---------------------------------------------------------------------------


def section_view(
    target: Any,
    column: ColumnData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
    scale: Any | None = None,
    unit: Any | None = None,
) -> dict[str, Any]:
    """Draw a column cross-section with perimeter tie, 135° seismic hooks touching the rebar,

    longitudinal bars located inside the tie, dimensions, and title.
    """
    ox, oy = origin
    w = column.section.width_in
    d = column.section.depth_in
    cover = column.section.cover_in

    scale = scale or getattr(column, "scale", None)
    unit = unit or getattr(column, "unit", None)
    is_metric = unit.is_metric if unit is not None else _detect_metric(column)

    if scale is not None or unit is not None:
        from struct_draw.core.units import DrawingScale, DrawingUnit, SCALE_1_20, SCALE_1_IN
        from struct_draw.style.annotation_config import DEFAULT_ANNOTATION_CONFIG
        d_unit = unit or (DrawingUnit.MM if is_metric else DrawingUnit.IN)
        d_scale = scale or (SCALE_1_20 if is_metric else SCALE_1_IN)
        text_height = DEFAULT_ANNOTATION_CONFIG.text_height(d_scale, d_unit)
        dim_offset = DEFAULT_ANNOTATION_CONFIG.dim_offset(d_scale, d_unit)
        dimstyle = "DIM_DETAIL" if is_metric else "Linear"
    else:
        dim_offset = 350.0 if is_metric else max(8.0, min(w, d) * 0.45)
        text_height = 120.0 if is_metric else 3.5
        dimstyle = "Linear"
    arrow_size = text_height * 0.65

    # Determine tie diameter and main bar diameter
    tie_size = column.stirrups.size or ("10M" if is_metric else "#3")
    tie_dia = _bar_diameter(tie_size, is_metric=is_metric)

    bars = list(column.longitudinal_bars) or [_corner_bar("C", i + 1) for i in range(4)]
    main_bar_size = bars[0].size if bars else ("20M" if is_metric else "#8")
    main_bar_dia = _bar_diameter(main_bar_size, is_metric=is_metric)
    r = main_bar_dia / 2.0

    # 1. Concrete Outline
    draw_concrete_outline(target, origin=(ox, oy), width=w, height=d, layer="COLUMN")

    # 2. Longitudinal Rebars (Placed inside the outer tie perimeter)
    bar_coords = _compute_rebar_coords(len(bars), w, d, cover, tie_dia, main_bar_dia)
    for bx, by in bar_coords:
        draw_rebar_circle(target, (ox + bx, oy + by), diameter=main_bar_dia, layer="REBAR")

    # 3. Double-line Closed Stirrup & 135° Seismic Hooks (Offset by cover from concrete face)
    sx0 = ox + cover
    sy0 = oy + cover
    sw = w - 2.0 * cover
    sh = d - 2.0 * cover

    if sw > 0 and sh > 0:
        from struct_draw.core.stirrup import StirrupGeometry

        hook_len = max(6.0 * tie_dia, 3.0 if not is_metric else 75.0)
        cos45 = math.sqrt(0.5)
        sin45 = math.sqrt(0.5)
        dx = hook_len * cos45
        dy = hook_len * sin45

        st_geom = StirrupGeometry(
            diameter=tie_dia,
            width=sw,
            depth=sh,
            origin=(sx0, sy0),
            hook_length=hook_len,
            hook_corner="top_left",
            corner_bar_diameter=main_bar_dia,
            double_line=True,
            layer="STIRRUP",
        )
        st_geom.draw(target)

        # If 8 or more bars, draw intermediate crosstie with 135° and 90° hooks
        if len(bars) >= 8:
            x_mid = (bar_coords[0][0] + bar_coords[2][0]) / 2.0
            y_mid = (bar_coords[0][1] + bar_coords[4][1]) / 2.0
            # Vertical crosstie
            draw_line(target, (ox + x_mid, sy0), (ox + x_mid, sy0 + sh), layer="STIRRUP")
            draw_line(target, (ox + x_mid, sy0 + sh), (ox + x_mid + dx * 0.75, sy0 + sh - dy * 0.75), layer="STIRRUP")
            # Horizontal crosstie
            draw_line(target, (sx0, oy + y_mid), (sx0 + sw, oy + y_mid), layer="STIRRUP")
            draw_line(target, (sx0 + sw, oy + y_mid), (sx0 + sw - dx * 0.75, oy + y_mid + dy * 0.75), layer="STIRRUP")

    # 5. Dimensions
    # Width dimension (bottom)
    draw_dimension(
        target,
        (ox, oy),
        (ox + w, oy),
        location=(ox + w / 2.0, oy - dim_offset),
        text_override=_format_dim(w, is_metric),
        layer="DIM_LINEAR",
    )
    # Depth dimension (left)
    draw_dimension(
        target,
        (ox, oy),
        (ox, oy + d),
        location=(ox - dim_offset, oy + d / 2.0),
        text_override=_format_dim(d, is_metric),
        layer="DIM_LINEAR",
    )

    # 6. Rebar Annotations using AutoCAD LEADER without criss-crossing
    lead_elbow_dx = dim_offset * 0.6
    lead_landing_len = dim_offset * 1.5

    # (a) Tie leader (Upper right area: pointing to top-right outer stirrup line)
    spacing = column.stirrups.spacing_in if column.stirrups.spacing_in > 0 else (150.0 if is_metric else 5.0)
    if is_metric:
        sp_str = f"{int(spacing)}mm" if spacing.is_integer() else f"{spacing:.1f}mm"
    else:
        sp_str = f'{int(spacing)}"' if spacing.is_integer() else f'{spacing:.1f}"'
    stirrup_text = f"{tie_size} @ {sp_str} c/c"

    pt_tie = (sx0 + sw, sy0 + sh * 0.75)
    elbow_tie = (ox + w + lead_elbow_dx, pt_tie[1])
    landing_tie = (elbow_tie[0] + lead_landing_len, elbow_tie[1])
    draw_leader(
        target,
        vertices=[pt_tie, elbow_tie, landing_tie],
        text=stirrup_text,
        arrow_size=arrow_size,
        text_height=text_height * 0.85,
        layer="LEADER",
    )

    # (b) Main rebar leader (Lower right area: pointing to Bottom-Right corner bar)
    # Bottom-right bar index is 1 in 4-bar and multi-bar layout
    br_idx = 1 if len(bar_coords) > 1 else 0
    pt_bar = (ox + bar_coords[br_idx][0], oy + bar_coords[br_idx][1])
    elbow_bar = (ox + w + lead_elbow_dx, pt_bar[1])
    landing_bar = (elbow_bar[0] + lead_landing_len, elbow_bar[1])
    draw_leader(
        target,
        vertices=[pt_bar, elbow_bar, landing_bar],
        text=f"{len(bars)} - {main_bar_size} MAIN BARS",
        arrow_size=arrow_size,
        text_height=text_height * 0.85,
        layer="LEADER",
    )

    # 7. Section View Title
    if title is None:
        title = f"SECTION @ {column.name}"
    title_pos = (ox + w / 2.0, oy - dim_offset * 1.8)
    draw_text(target, title, position=title_pos, height=text_height * 1.2, layer="TITLE")

    scale_text = "SCALE 1:20" if is_metric else 'SCALE: 3/4" = 1\'-0"'
    draw_text(target, scale_text, position=(ox + w / 2.0, title_pos[1] - text_height * 1.4), height=text_height * 0.75, layer="TEXT")

    # Bounding box
    min_x = ox - dim_offset * 1.8
    max_x = max(landing_bar[0], landing_tie[0]) + text_height * 8.0
    min_y = title_pos[1] - text_height * 3.0
    max_y = oy + d + dim_offset * 0.6

    refs: dict[str, Any] = {
        "origin": (ox, oy),
        "section_origin": (ox, oy),
        "width": w,
        "depth": d,
        "bounding_box": (min_x, min_y, max_x, max_y),
    }
    return refs


# ---------------------------------------------------------------------------
# Elevation View (ACI 318 Seismic Detailing)
# ---------------------------------------------------------------------------


def elevation_view(
    target: Any,
    column: ColumnData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
    break_line_at: float | None = None,
    scale: Any | None = None,
    unit: Any | None = None,
) -> dict[str, Any]:
    """Draw a professional column elevation detailing adhering strictly to ACI 318 seismic provisions:

    * Confinement regions Lo at top and bottom ends (ACI 318 §18.7.5.1)
    * First hoop placed <= 2" (50mm) from joint faces
    * Central region with typical tie spacing
    * Lap splice strictly confined to mid-height (ACI 318 §18.7.4.3) with 1:6 crank
    * Transverse reinforcement continued through beam-column joint (ACI 318 §18.8.3)
    * AutoCAD LEADER callouts with inclined pointer lines, landing shoulders, and clean two-line text
    * Clean level lines, full dimension hierarchy, and detailed notes
    """
    ox, oy = origin
    w = column.section.width_in
    d = column.section.depth_in
    H = column.height_in
    cover = column.section.cover_in

    scale = scale or getattr(column, "scale", None)
    unit = unit or getattr(column, "unit", None)
    is_metric = unit.is_metric if unit is not None else _detect_metric(column)

    if scale is not None or unit is not None:
        from struct_draw.core.units import DrawingScale, DrawingUnit, SCALE_1_25, SCALE_1_IN
        from struct_draw.style.annotation_config import DEFAULT_ANNOTATION_CONFIG
        d_unit = unit or (DrawingUnit.MM if is_metric else DrawingUnit.IN)
        d_scale = scale or (SCALE_1_25 if is_metric else SCALE_1_IN)
        text_height = DEFAULT_ANNOTATION_CONFIG.text_height(d_scale, d_unit)
        dim_offset = DEFAULT_ANNOTATION_CONFIG.dim_offset(d_scale, d_unit)
        dimstyle = "DIM_DETAIL" if is_metric else "Linear"
    else:
        dim_offset = 350.0 if is_metric else max(8.0, w * 0.45)
        text_height = 120.0 if is_metric else 3.5
        dimstyle = "Linear"
    arrow_size = text_height * 0.65

    # Framing member depths (upper beam and lower footing / foundation beam)
    h_beam = min(H * 0.2, 600.0 if is_metric else 24.0)
    beam_ext = 800.0 if is_metric else 30.0

    # Bar sizes and diameters
    tie_size = column.stirrups.size or ("10M" if is_metric else "#3")
    tie_dia = _bar_diameter(tie_size, is_metric=is_metric)

    bars = list(column.longitudinal_bars) or [_corner_bar("C", i + 1) for i in range(4)]
    main_bar_size = bars[0].size if bars else ("20M" if is_metric else "#8")
    main_bar_dia = _bar_diameter(main_bar_size, is_metric=is_metric)

    # -----------------------------------------------------------------------
    # 1. ACI 318 Seismic Parameters Calculation
    # -----------------------------------------------------------------------
    lo_min_abs = 450.0 if is_metric else 18.0
    lo = max(w, d, H / 6.0, lo_min_abs)
    lo = min(lo, H * 0.35)

    # Seismic hoop spacing in Lo region: so <= min(w/4, d/4, 6*db, 6" / 150mm)
    so_max = min(w / 4.0, d / 4.0, 6.0 * main_bar_dia, 100.0 if is_metric else 4.0)
    so = max(50.0 if is_metric else 3.0, min(so_max, column.stirrups.spacing_in / 2.0 if column.stirrups.spacing_in > 0 else 4.0))

    # Central zone tie spacing s
    s_mid = max(so * 1.5, column.stirrups.spacing_in if column.stirrups.spacing_in > 0 else (200.0 if is_metric else 8.0))

    # Joint hoop spacing
    s_joint = max(so, 150.0 if is_metric else 6.0)

    # Class B Lap splice length: Ld = max(48 * db, 30" / 750mm)
    l_splice = max(48.0 * main_bar_dia, 750.0 if is_metric else 30.0)
    l_splice = min(l_splice, (H - 2.0 * lo) * 0.85)

    # Lap splice location: centered at mid-height (H/2) (ACI 318 §18.7.4.3)
    y_mid = oy + H / 2.0
    y_splice_bot = y_mid - l_splice / 2.0
    y_splice_top = y_mid + l_splice / 2.0

    # -----------------------------------------------------------------------
    # 2. Concrete Framing Outline (Column + Upper/Lower Beams/Slabs)
    # -----------------------------------------------------------------------
    # Main Column Shaft
    draw_rectangle(target, origin=(ox, oy), width=w, height=H, layer="COLUMN")

    # Lower framing (Floor / Footing / Foundation Beam)
    jog_beam = min(beam_ext * 0.15, 30.0 if is_metric else 1.5)
    draw_line(target, (ox - beam_ext, oy), (ox, oy), layer="COLUMN")
    draw_line(target, (ox + w, oy), (ox + w + beam_ext, oy), layer="COLUMN")
    draw_line(target, (ox - beam_ext, oy - h_beam), (ox + w + beam_ext, oy - h_beam), layer="COLUMN")
    draw_break_line(target, p1=(ox - beam_ext, oy), p2=(ox - beam_ext, oy - h_beam), jog=jog_beam, layer="BREAK_LINE")
    draw_break_line(target, p1=(ox + w + beam_ext, oy), p2=(ox + w + beam_ext, oy - h_beam), jog=jog_beam, layer="BREAK_LINE")

    # Upper framing (Floor Beam / Slab)
    draw_line(target, (ox - beam_ext, oy + H), (ox, oy + H), layer="COLUMN")
    draw_line(target, (ox + w, oy + H), (ox + w + beam_ext, oy + H), layer="COLUMN")
    draw_line(target, (ox - beam_ext, oy + H + h_beam), (ox + w + beam_ext, oy + H + h_beam), layer="COLUMN")
    draw_break_line(target, p1=(ox - beam_ext, oy + H), p2=(ox - beam_ext, oy + H + h_beam), jog=jog_beam, layer="BREAK_LINE")
    draw_break_line(target, p1=(ox + w + beam_ext, oy + H), p2=(ox + w + beam_ext, oy + H + h_beam), jog=jog_beam, layer="BREAK_LINE")

    # Column shaft continuing above upper floor (starter stub)
    h_stub = min(H * 0.25, 450.0 if is_metric else 18.0)
    draw_line(target, (ox, oy + H + h_beam), (ox, oy + H + h_beam + h_stub), layer="COLUMN")
    draw_line(target, (ox + w, oy + H + h_beam), (ox + w, oy + H + h_beam + h_stub), layer="COLUMN")
    draw_break_line(target, p1=(ox, oy + H + h_beam + h_stub), p2=(ox + w, oy + H + h_beam + h_stub), jog=jog_beam, layer="BREAK_LINE")

    # -----------------------------------------------------------------------
    # 3. Longitudinal Reinforcement & Seismic Lap Splice
    # -----------------------------------------------------------------------
    bar_coords = _compute_rebar_coords(len(bars), w, d, cover, tie_dia, main_bar_dia)
    x_left = bar_coords[0][0]
    x_right = bar_coords[1][0] if len(bar_coords) > 1 else (w - x_left)

    crank_offset = main_bar_dia * 1.1
    crank_h = crank_offset * 6.0

    # Lower longitudinal bars (legs bending outward into beam/foundation reinforcement)
    hook_ext = min(w * 0.4, 250.0 if is_metric else 10.0)
    pts_left_bot = [
        (ox + x_left - hook_ext, oy - h_beam + cover * 1.5),
        (ox + x_left, oy - h_beam + cover * 1.5),
        (ox + x_left, y_splice_top),
    ]
    draw_polyline(target, pts_left_bot, close=False, layer="REBAR")

    pts_right_bot = [
        (ox + x_right + hook_ext, oy - h_beam + cover * 1.5),
        (ox + x_right, oy - h_beam + cover * 1.5),
        (ox + x_right, y_splice_top),
    ]
    draw_polyline(target, pts_right_bot, close=False, layer="REBAR")

    # Upper longitudinal bars with 1:6 crank
    pts_left_top = [
        (ox + x_left + crank_offset, y_splice_bot),
        (ox + x_left + crank_offset, y_splice_bot + crank_h),
        (ox + x_left, y_splice_bot + crank_h * 2.0),
        (ox + x_left, oy + H + h_beam + h_stub - cover),
    ]
    draw_polyline(target, pts_left_top, close=False, layer="REBAR")

    pts_right_top = [
        (ox + x_right - crank_offset, y_splice_bot),
        (ox + x_right - crank_offset, y_splice_bot + crank_h),
        (ox + x_right, y_splice_bot + crank_h * 2.0),
        (ox + x_right, oy + H + h_beam + h_stub - cover),
    ]
    draw_polyline(target, pts_right_top, close=False, layer="REBAR")

    # If 6 or 8 bars, draw center bar lines
    if len(bars) >= 6:
        x_center = (x_left + x_right) / 2.0
        draw_line(target, (ox + x_center, oy - h_beam + cover * 1.5), (ox + x_center, y_splice_top), layer="REBAR")
        draw_line(target, (ox + x_center + crank_offset, y_splice_bot), (ox + x_center, y_splice_bot + crank_h * 2.0), layer="REBAR")
        draw_line(target, (ox + x_center, y_splice_bot + crank_h * 2.0), (ox + x_center, oy + H + h_beam + h_stub - cover), layer="REBAR")

    # -----------------------------------------------------------------------
    # 4. Transverse Reinforcement (Hoops & Ties)
    # -----------------------------------------------------------------------
    tie_x1 = ox + cover
    tie_x2 = ox + w - cover

    # (a) Bottom Confinement Zone Lo
    first_tie_offset = min(50.0 if is_metric else 2.0, so / 2.0)
    y_curr = oy + first_tie_offset
    while y_curr <= oy + lo:
        draw_line(target, (tie_x1, y_curr), (tie_x2, y_curr), layer="STIRRUP")
        y_curr += so

    # (b) Central Region
    while y_curr < oy + H - lo:
        draw_line(target, (tie_x1, y_curr), (tie_x2, y_curr), layer="STIRRUP")
        if y_splice_bot <= y_curr <= y_splice_top:
            y_curr += so
        else:
            y_curr += s_mid

    # (c) Top Confinement Zone Lo
    y_top_start = max(y_curr, oy + H - lo)
    y_curr = y_top_start
    while y_curr <= oy + H - first_tie_offset:
        draw_line(target, (tie_x1, y_curr), (tie_x2, y_curr), layer="STIRRUP")
        y_curr += so

    # (d) Hoops through Beam-Column Joint
    y_joint = oy + H + so
    while y_joint <= oy + H + h_beam - first_tie_offset:
        draw_line(target, (tie_x1, y_joint), (tie_x2, y_joint), layer="STIRRUP")
        y_joint += s_joint

    # (e) Hoops in column stub above joint
    y_stub = oy + H + h_beam + first_tie_offset
    while y_stub <= oy + H + h_beam + h_stub - first_tie_offset:
        draw_line(target, (tie_x1, y_stub), (tie_x2, y_stub), layer="STIRRUP")
        y_stub += so

    # -----------------------------------------------------------------------
    # 5. Level Lines and Structural Markers
    # -----------------------------------------------------------------------
    level_ext = dim_offset * 1.2
    draw_line(target, (ox - level_ext, oy), (ox + w + level_ext, oy), layer="LEVEL")
    draw_text(target, "LEVEL N (TOP OF SLAB / BEAM)", position=(ox + w + level_ext + (30.0 if is_metric else 1.5), oy), height=text_height * 0.85, layer="TEXT")

    draw_line(target, (ox - level_ext, oy + H), (ox + w + level_ext, oy + H), layer="LEVEL")
    draw_text(target, "BEAM SOFFIT", position=(ox + w + level_ext + (30.0 if is_metric else 1.5), oy + H), height=text_height * 0.85, layer="TEXT")

    draw_line(target, (ox - level_ext, oy + H + h_beam), (ox + w + level_ext, oy + H + h_beam), layer="LEVEL")
    draw_text(target, "LEVEL N+1 (FLOOR LEVEL)", position=(ox + w + level_ext + (30.0 if is_metric else 1.5), oy + H + h_beam), height=text_height * 0.85, layer="TEXT")

    # -----------------------------------------------------------------------
    # 6. Dimension Chains (Left of Column)
    # -----------------------------------------------------------------------
    dim_x1 = ox - dim_offset * 0.9
    dim_x2 = ox - dim_offset * 1.8
    dim_x3 = ox - dim_offset * 2.7

    # Chain 1: Lo, Central Zone, Top Lo, Joint Beam Depth
    draw_dimension(
        target,
        (ox, oy),
        (ox, oy + lo),
        location=(dim_x1, oy + lo / 2.0),
        text_override=f"Lo = {_format_dim(lo, is_metric)}",
        layer="DIM_LINEAR",
    )
    draw_dimension(
        target,
        (ox, oy + lo),
        (ox, oy + H - lo),
        location=(dim_x1, oy + H / 2.0),
        text_override=_format_dim(H - 2.0 * lo, is_metric),
        layer="DIM_LINEAR",
    )
    draw_dimension(
        target,
        (ox, oy + H - lo),
        (ox, oy + H),
        location=(dim_x1, oy + H - lo / 2.0),
        text_override=f"Lo = {_format_dim(lo, is_metric)}",
        layer="DIM_LINEAR",
    )
    draw_dimension(
        target,
        (ox, oy + H),
        (ox, oy + H + h_beam),
        location=(dim_x1, oy + H + h_beam / 2.0),
        text_override=_format_dim(h_beam, is_metric),
        layer="DIM_LINEAR",
    )

    # Chain 2: Clear Height Lu
    draw_dimension(
        target,
        (ox, oy),
        (ox, oy + H),
        location=(dim_x2, oy + H / 2.0),
        text_override=f"Lu = {_format_dim(H, is_metric)}",
        layer="DIM_LINEAR",
    )

    # Chain 3: Total Story Height
    draw_dimension(
        target,
        (ox, oy),
        (ox, oy + H + h_beam),
        location=(dim_x3, oy + (H + h_beam) / 2.0),
        text_override=f"STORY H = {_format_dim(H + h_beam, is_metric)}",
        layer="DIM_LINEAR",
    )

    # Column Width at Top
    draw_dimension(
        target,
        (ox, oy + H + h_beam + h_stub),
        (ox + w, oy + H + h_beam + h_stub),
        location=(ox + w / 2.0, oy + H + h_beam + h_stub + dim_offset * 0.8),
        text_override=_format_dim(w, is_metric),
        layer="DIM_LINEAR",
    )

    # -----------------------------------------------------------------------
    # 7. AutoCAD LEADER Seismic Annotations with 2-segment inclined lines & two-line text
    # -----------------------------------------------------------------------
    ann_elbow_dx = dim_offset * 0.8
    landing_w = dim_offset * 2.0
    unit_str = "mm" if is_metric else '"'

    # (a) Joint hoops callout
    so_joint_str = f"{s_joint:.0f}" if s_joint.is_integer() else f"{s_joint:.1f}"
    pt_a = (tie_x2, oy + H + h_beam * 0.5)
    elbow_a = (ox + w + ann_elbow_dx, pt_a[1])
    landing_a = (elbow_a[0] + landing_w, elbow_a[1])
    draw_leader(
        target,
        vertices=[pt_a, elbow_a, landing_a],
        text=f"{tie_size} HOOPS @ {so_joint_str}{unit_str} C/C\n(THROUGH JOINT PER ACI 318 §18.8.3)",
        arrow_size=arrow_size,
        text_height=text_height * 0.85,
        layer="LEADER",
    )

    # (b) Top Lo zone hoops callout
    so_str = f"{so:.0f}" if so.is_integer() else f"{so:.1f}"
    pt_b = (tie_x2, oy + H - lo * 0.4)
    elbow_b = (ox + w + ann_elbow_dx, pt_b[1])
    landing_b = (elbow_b[0] + landing_w, elbow_b[1])
    draw_leader(
        target,
        vertices=[pt_b, elbow_b, landing_b],
        text=f"Lo REGION: {tie_size} HOOPS @ {so_str}{unit_str} C/C\n(135° SEISMIC HOOKS, EXTEND >= 6db)",
        arrow_size=arrow_size,
        text_height=text_height * 0.85,
        layer="LEADER",
    )

    # (c) Lap splice zone callout (Mid-height)
    l_splice_str = _format_dim(l_splice, is_metric)
    pt_c = (ox + x_right, y_mid)
    elbow_c = (ox + w + ann_elbow_dx, y_mid)
    landing_c = (elbow_c[0] + landing_w, elbow_c[1])
    draw_leader(
        target,
        vertices=[pt_c, elbow_c, landing_c],
        text=f"LAP SPLICE: Ld = {l_splice_str}\n(CLASS B, MID-HEIGHT PER ACI 318 §18.7.4.3)",
        arrow_size=arrow_size,
        text_height=text_height * 0.85,
        layer="LEADER",
    )

    # (d) Central region ties callout
    smid_str = f"{s_mid:.0f}" if s_mid.is_integer() else f"{s_mid:.1f}"
    y_mid_ties = oy + lo + (y_splice_bot - (oy + lo)) * 0.5
    pt_d = (tie_x2, y_mid_ties)
    elbow_d = (ox + w + ann_elbow_dx, y_mid_ties)
    landing_d = (elbow_d[0] + landing_w, elbow_d[1])
    draw_leader(
        target,
        vertices=[pt_d, elbow_d, landing_d],
        text=f"CENTRAL REGION: {tie_size} TIES @ {smid_str}{unit_str} C/C\n(TYPICAL TRANSVERSE TIES)",
        arrow_size=arrow_size,
        text_height=text_height * 0.85,
        layer="LEADER",
    )

    # (e) Bottom Lo zone hoops callout (positioned safely above Level N line and text)
    pt_e = (tie_x2, oy + lo * 0.75)
    elbow_e = (ox + w + ann_elbow_dx, pt_e[1])
    landing_e = (elbow_e[0] + landing_w, elbow_e[1])
    draw_leader(
        target,
        vertices=[pt_e, elbow_e, landing_e],
        text=f"Lo REGION: {tie_size} HOOPS @ {so_str}{unit_str} C/C\n(FIRST HOOP <= 2\" [50mm] FROM JOINT)",
        arrow_size=arrow_size,
        text_height=text_height * 0.85,
        layer="LEADER",
    )

    # (f) Longitudinal rebar callout
    pt_f = (ox + x_right, oy - h_beam * 0.5)
    elbow_f = (ox + w + ann_elbow_dx, pt_f[1])
    landing_f = (elbow_f[0] + landing_w, elbow_f[1])
    draw_leader(
        target,
        vertices=[pt_f, elbow_f, landing_f],
        text=f"MAIN REBAR: {len(bars)} - {main_bar_size} CONTINUOUS\n(1:6 CRANK AT SPLICE, 90° HOOK AT BASE)",
        arrow_size=arrow_size,
        text_height=text_height * 0.85,
        layer="LEADER",
    )

    # -----------------------------------------------------------------------
    # 8. Elevation View Title & Scale
    # -----------------------------------------------------------------------
    if title is None:
        title = f"ELEVATION OF {column.name}"
    title_pos = (ox + w / 2.0, oy - h_beam - dim_offset * 1.5)
    draw_text(target, title, position=title_pos, height=text_height * 1.2, layer="TITLE")

    scale_text = "SCALE 1:25" if is_metric else 'SCALE: 1/2" = 1\'-0"'
    draw_text(target, scale_text, position=(ox + w / 2.0, title_pos[1] - text_height * 1.4), height=text_height * 0.75, layer="TEXT")

    # -----------------------------------------------------------------------
    # 9. ACI 318 Seismic Detailing General Notes Block
    # -----------------------------------------------------------------------
    notes_x = ox - dim_offset * 2.7
    notes_y = title_pos[1] - text_height * 4.0
    notes = [
        "ACI 318-19 SEISMIC COLUMN DETAILING NOTES:",
        "1. CONFINEMENT LENGTH Lo = MAX(h, b, H/6, 18\" [450mm]) AT COLUMN ENDS (ACI 318 §18.7.5.1).",
        "2. FIRST HOOP LOCATED AT <= 2.0\" (50mm) FROM JOINT FACE (ACI 318 §18.7.5.3).",
        "3. ALL HOOPS PROVIDED WITH 135° SEISMIC HOOKS WITH >= 6db EXTENSION INTO CORE.",
        "4. LAP SPLICES PERMITTED ONLY WITHIN CENTER HALF OF COLUMN CLEAR HEIGHT (ACI 318 §18.7.4.3).",
        "5. HOOPS CONTINUED THROUGH BEAM-COLUMN JOINT PER ACI 318 §18.8.3.",
        "6. CLEAR COVER = 1.5\" (40mm) TO OUTER FACE OF TRANSVERSE HOOPS.",
    ]
    for idx, note in enumerate(notes):
        n_layer = "TITLE" if idx == 0 else "TEXT"
        n_ht = text_height * 0.85 if idx == 0 else text_height * 0.7
        draw_text(target, note, position=(notes_x, notes_y - idx * text_height * 1.3), height=n_ht, layer=n_layer)

    # -----------------------------------------------------------------------
    # 10. Bounding Box Calculation
    # -----------------------------------------------------------------------
    max_callout_text_len = 55
    leader_text_width = max_callout_text_len * text_height * 0.75
    min_x = dim_x3 - dim_offset * 0.8
    max_x = landing_c[0] + leader_text_width + dim_offset
    min_y = notes_y - len(notes) * text_height * 1.5
    max_y = oy + H + h_beam + h_stub + dim_offset * 1.5

    refs: dict[str, Any] = {
        "origin": (ox, oy),
        "elevation_origin": (ox, oy),
        "width": w,
        "height": H,
        "lo": lo,
        "so": so,
        "l_splice": l_splice,
        "bounding_box": (min_x, min_y, max_x, max_y),
    }
    return refs


# ---------------------------------------------------------------------------
# Master Drawing (Dynamic Layout)
# ---------------------------------------------------------------------------


def drawing(
    target: Any,
    column: ColumnData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
    layout: str = "side_by_side",
    scale: Any = None,
    unit: Any = None,
) -> dict[str, Any]:
    """Draw a complete ACI 318 column drawing with dynamic positioning of elevation and section.

    In ``"side_by_side"`` layout (default), the longitudinal elevation is placed
    on the left and the cross-section is placed dynamically on the right, centered
    along the height with zero overlap.

    In ``"stacked"`` layout, the section is placed safely above/below the elevation
    using the bounding box calculations to guarantee zero overlap.
    """
    ox, oy = origin
    is_metric = _detect_metric(column)
    w = column.section.width_in
    d = column.section.depth_in
    H = column.height_in

    if layout == "stacked":
        # Draw section above elevation with safe dynamic clearance
        refs_elev = elevation_view(target, column, origin=(ox, oy), title=title or f"ELEVATION OF {column.name}", scale=scale, unit=unit)
        elev_bbox = refs_elev["bounding_box"]
        margin_y = max(d * 2.0, 40.0 if not is_metric else 1000.0)
        sec_y = elev_bbox[3] + margin_y
        refs_sec = section_view(target, column, origin=(ox, sec_y), title=f"SECTION @ {column.name}", scale=scale, unit=unit)
        sec_bbox = refs_sec["bounding_box"]
    else:
        # Default: side_by_side
        # 1. Draw Elevation on the left
        refs_elev = elevation_view(target, column, origin=(ox, oy), title=title or f"ELEVATION OF {column.name}", scale=scale, unit=unit)
        elev_bbox = refs_elev["bounding_box"]

        # 2. Compute dynamic margin to the right of elevation's outer bounding box (clearing all leader text)
        margin_x = max(w * 2.0, 45.0 if not is_metric else 1100.0)
        sec_x = elev_bbox[2] + margin_x
        sec_y = oy + max(0.0, (H - d) / 2.0)

        # 3. Draw Section on the right
        refs_sec = section_view(target, column, origin=(sec_x, sec_y), title=f"SECTION @ {column.name}", scale=scale, unit=unit)
        sec_bbox = refs_sec["bounding_box"]

    refs_sched = None
    if column.schedule:
        from struct_draw.core.composite import draw_schedule_table
        from struct_draw.core.data import ScheduleTableData
        sched_title = f"{column.name} REBAR SCHEDULE"
        sched_data = ScheduleTableData(
            title=sched_title,
            rows=column.schedule,
            unit="mm" if is_metric else "in",
            scale=scale,
        )
        if layout == "stacked":
            sched_y = elev_bbox[1] - (30.0 if not is_metric else 800.0)
            refs_sched = draw_schedule_table(target, sched_data, origin=(ox, sched_y), scale=scale, unit=unit)
        else:
            sched_x = sec_bbox[0]
            sched_y = sec_bbox[1] - (30.0 if not is_metric else 800.0)
            refs_sched = draw_schedule_table(target, sched_data, origin=(sched_x, sched_y), scale=scale, unit=unit)

    min_x = min(elev_bbox[0], sec_bbox[0])
    min_y = min(elev_bbox[1], sec_bbox[1])
    max_x = max(elev_bbox[2], sec_bbox[2])
    max_y = max(elev_bbox[3], sec_bbox[3])

    if refs_sched is not None:
        sb = refs_sched["bounding_box"]
        min_x = min(min_x, sb[0])
        min_y = min(min_y, sb[1])
        max_x = max(max_x, sb[2])
        max_y = max(max_y, sb[3])

    result: dict[str, Any] = {
        "elevation": refs_elev,
        "section": refs_sec,
        "bounding_box": (min_x, min_y, max_x, max_y),
    }
    if refs_sched is not None:
        result["schedule"] = refs_sched
    return result


__all__ = ["section_view", "elevation_view", "drawing"]
