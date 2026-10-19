"""struct_draw.elements.combined_footing — Plan + section views for combined footings.

This module implements detailed, production-ready structural drawing functions
for combined footings (two columns supported on a single footing pad) based on the
reference standard in ``references/combined_footing.py``.

Key features:
* Accurate geometry for rectangular combined footing pads supporting 2 columns.
* Sub-base PCC (Plain Cement Concrete) and Flat Brick Soling layers with proper hatches.
* Plinth Beam and Foundation Beam cross-section details.
* Column stems elevation with top break line symbols.
* Ground Level (GL) and Plinth Level (PL) markers and level extension lines.
* Complete reinforcement detailing:
  - Bottom and top main rebar layers with vertical anchorage end hooks.
  - Transverse rebar dots in section view.
  - Column vertical longitudinal steel extending down into the footing pad with Ld bends.
  - Development length "Ld" bracket annotation and text callout.
  - Column stirrups / rings along the column stems.
* Multileader callouts for rebar, columns, stirrups, beams, PCC, and soling.
* Plan view with footing pad, columns, centerlines (CEN layer with CENTER linetype),
  rebar indicators, and complete horizontal/vertical dimensions.
"""

from __future__ import annotations

from typing import Any

from struct_draw.core.composite import (
    draw_beam_section,
    draw_break_line,
    draw_dimension,
    draw_hatch,
    draw_leader,
    draw_line,
    draw_polyline,
    draw_rebar_circle,
    draw_stirrup_hooked,
    draw_text,
)
from struct_draw.core.data import CombinedFootingData
from struct_draw.core.primitives import draw_rectangle


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
        0.375: "#3",
        0.5: "#4",
        0.625: "#5",
        0.75: "#6",
        0.875: "#7",
        1.0: "#8",
        1.128: "#9",
        1.27: "#10",
        1.41: "#11",
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


def section_view(
    target: Any,
    combined_footing: CombinedFootingData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
    scale: Any | None = None,
    unit: Any | None = None,
) -> dict[str, Any]:
    """Draw a full cross-section view of a combined footing."""
    ox, oy = origin
    proj_left = combined_footing.proj_left_in
    proj_right = combined_footing.proj_right_in
    col_sp = combined_footing.col_spacing_in
    L = combined_footing.total_length_in
    thick = combined_footing.thickness_in
    width = combined_footing.width_in
    cw1 = combined_footing.col1_width_in
    cd1 = combined_footing.col1_depth_in
    cw2 = combined_footing.col2_width_in
    cd2 = combined_footing.col2_depth_in
    fd = combined_footing.footing_depth_in
    pl = combined_footing.plinth_height_in
    cover = combined_footing.cover_in
    bar_dia = combined_footing.bar_dia_in
    bar_spacing = combined_footing.bar_spacing_in
    top_bar_dia = combined_footing.top_bar_dia_in or bar_dia
    top_bar_spacing = combined_footing.top_bar_spacing_in or bar_spacing
    Ld = combined_footing.development_length_in
    pcc_thick = combined_footing.pcc_thickness_in
    soling_thick = combined_footing.soling_thickness_in

    scale = scale or getattr(combined_footing, "scale", None)
    unit = unit or getattr(combined_footing, "unit", None)
    if unit is not None:
        from struct_draw.core.units import DrawingUnit
        is_metric = DrawingUnit.from_str(unit).is_metric if isinstance(unit, str) else getattr(unit, "is_metric", True)
    else:
        is_metric = L >= 300.0
    s = 1.0 if is_metric else 1.0 / 25.4

    if is_metric:
        if cw1 < 50.0:
            cw1 = cw1 * 25.4
        if cd1 < 50.0:
            cd1 = cd1 * 25.4
        if cw2 < 50.0:
            cw2 = cw2 * 25.4
        if cd2 < 50.0:
            cd2 = cd2 * 25.4
        if pcc_thick < 10.0 and pcc_thick > 0:
            pcc_thick = pcc_thick * 25.4
        if soling_thick < 10.0 and soling_thick > 0:
            soling_thick = soling_thick * 25.4
        if Ld < 50.0:
            Ld = Ld * 25.4

    if scale is not None or unit is not None:
        from struct_draw.core.units import DrawingScale, DrawingUnit, SCALE_1_25, SCALE_1_IN
        from struct_draw.style.annotation_config import DEFAULT_ANNOTATION_CONFIG
        d_unit = unit or (DrawingUnit.MM if is_metric else DrawingUnit.IN)
        d_scale = scale or (SCALE_1_25 if is_metric else SCALE_1_IN)
        txt_sz = DEFAULT_ANNOTATION_CONFIG.text_height(d_scale, d_unit)
        st_sz = DEFAULT_ANNOTATION_CONFIG.dim_text_height(d_scale, d_unit)
        title_sz = DEFAULT_ANNOTATION_CONFIG.text_height(d_scale, d_unit)
    else:
        txt_sz = 100.0 * s
        st_sz = 80.0 * s
        title_sz = 100.0 * s

    pb_w = combined_footing.plinth_beam_width_in or (230.0 if is_metric else 9.0)
    pb_h = combined_footing.plinth_beam_depth_in or (350.0 if is_metric else 14.0)
    fb_w = combined_footing.foundation_beam_width_in or (230.0 if is_metric else 9.0)
    fb_h = combined_footing.foundation_beam_depth_in or (300.0 if is_metric else 12.0)

    # Column center coordinates
    cx1 = ox
    cx2 = ox + col_sp
    x_left = cx1 - proj_left
    x_right = cx2 + proj_right

    col1_left = cx1 - cw1 / 2.0
    col1_right = cx1 + cw1 / 2.0
    col2_left = cx2 - cw2 / 2.0
    col2_right = cx2 + cw2 / 2.0

    # 1. Footing Pad Concrete Outline
    pad_pts = [
        (x_left, oy),
        (x_right, oy),
        (x_right, oy + thick),
        (x_left, oy + thick),
    ]
    draw_polyline(target, pad_pts, close=True, layer="Foundation")

    # 2. Sub-base PCC layer
    if pcc_thick > 0:
        pcc_pts = [
            (x_left, oy),
            (x_right, oy),
            (x_right, oy - pcc_thick),
            (x_left, oy - pcc_thick),
        ]
        draw_polyline(target, pcc_pts, close=True, layer="Foundation")
        draw_hatch(
            target,
            paths=[{"type": "polyline", "points": pcc_pts, "is_closed": True}],
            pattern="AR-CONC",
            scale=15.0 if is_metric else 0.6,
            layer="HATCH",
        )

    # 3. Sub-base Soling layer (Brick or Stone)
    if soling_thick > 0:
        sol_pts = [
            (x_left, oy - pcc_thick),
            (x_right, oy - pcc_thick),
            (x_right, oy - pcc_thick - soling_thick),
            (x_left, oy - pcc_thick - soling_thick),
        ]
        draw_polyline(target, sol_pts, close=True, layer="Foundation")
        sol_mat = getattr(combined_footing, "soling_material", "brick").lower()
        is_stone = sol_mat == "stone"
        sol_pattern = "GRAVEL" if is_stone else "ANSI32"
        sol_scale = (15.0 if is_metric else 0.6) if is_stone else (100.0 if is_metric else 4.0)
        draw_hatch(
            target,
            paths=[{"type": "polyline", "points": sol_pts, "is_closed": True}],
            pattern=sol_pattern,
            scale=sol_scale,
            layer="HATCH",
        )

    # 4. Columns (Col 1 and Col 2 stems)
    ext_top = 400.0 * s
    col_y_top = fd + pl + ext_top + oy

    # Col 1 stem
    draw_line(target, (col1_left, thick + oy), (col1_left, col_y_top), layer="Column")
    draw_line(target, (col1_right, thick + oy), (col1_right, col_y_top), layer="Column")
    draw_break_line(
        target,
        p1=(col1_left - 50.0 * s, col_y_top),
        p2=(col1_right + 50.0 * s, col_y_top),
        layer="Column",
    )

    # Col 2 stem
    draw_line(target, (col2_left, thick + oy), (col2_left, col_y_top), layer="Column")
    draw_line(target, (col2_right, thick + oy), (col2_right, col_y_top), layer="Column")
    draw_break_line(
        target,
        p1=(col2_left - 50.0 * s, col_y_top),
        p2=(col2_right + 50.0 * s, col_y_top),
        layer="Column",
    )

    # 5. Level Lines (GL & PL)
    gl_y = fd + oy
    pl_y = fd + pl + oy
    dim_off = (DEFAULT_ANNOTATION_CONFIG.dim_offset(d_scale, d_unit) if (scale is not None or unit is not None) else 300.0)
    level_ext = max(1800.0 if is_metric else 72.0, dim_off * 4.5)
    draw_line(target, (col1_left, gl_y), (col1_left - level_ext, gl_y), layer="Level")
    txt_x = col1_left - level_ext + (50.0 if is_metric else 2.0)
    draw_text(
        target,
        "Ground Lvl.",
        position=(txt_x, gl_y + st_sz * 0.25),
        height=st_sz,
        align="bottom_left",
        layer="Text",
    )
    draw_line(target, (col1_left, pl_y), (col1_left - level_ext, pl_y), layer="Level")
    draw_text(
        target,
        "Plinth Lvl.",
        position=(txt_x, pl_y + st_sz * 0.25),
        height=st_sz,
        align="bottom_left",
        layer="Text",
    )

    # 6. Plinth Beams and Foundation Beams (if present)
    if pb_w > 0 and pb_h > 0:
        for cx in (cx1, cx2):
            draw_beam_section(
                target,
                center_x=cx,
                top_y=pl_y,
                width=pb_w,
                height=pb_h,
                is_metric=is_metric,
            )

    if fb_w > 0 and fb_h > 0:
        for cx in (cx1, cx2):
            draw_beam_section(
                target,
                center_x=cx,
                top_y=thick + oy + fb_h,
                width=fb_w,
                height=fb_h,
                is_metric=is_metric,
            )

    # 7. Reinforcement Steel
    # Bottom main longitudinal bar
    p7_x = x_left + (70.0 if is_metric else cover)
    p8_x = x_right - (70.0 if is_metric else cover)
    bot_y = oy + (50.0 if is_metric else cover + bar_dia / 2.0)
    hook_h = 80.0 if is_metric else 3.0

    draw_polyline(
        target,
        [
            (p7_x, bot_y + hook_h),
            (p7_x, bot_y),
            (p8_x, bot_y),
            (p8_x, bot_y + hook_h),
        ],
        close=False,
        layer="Rebar",
    )

    # Top main longitudinal bar
    top_y = oy + thick - (50.0 if is_metric else cover + top_bar_dia / 2.0)
    draw_polyline(
        target,
        [
            (p7_x, top_y - hook_h),
            (p7_x, top_y),
            (p8_x, top_y),
            (p8_x, top_y - hook_h),
        ],
        close=False,
        layer="Rebar",
    )

    # Transverse rebar dots
    dot_r = (top_bar_dia if top_bar_dia else bar_dia) / 2.0
    step_sz = 100.0 * s
    n_bot_dots = max(1, int((p8_x - p7_x) / step_sz))
    actual_step = (p8_x - p7_x) / n_bot_dots
    for i in range(n_bot_dots + 1):
        dot_x = p7_x + i * actual_step
        draw_rebar_circle(
            target,
            (dot_x, bot_y + (10.0 if is_metric else 0.4)),
            diameter=dot_r * 2.0,
            layer="Rebar_hatch",
        )
        draw_rebar_circle(
            target,
            (dot_x, top_y - (10.0 if is_metric else 0.4)),
            diameter=dot_r * 2.0,
            layer="Rebar_hatch",
        )

    # Column vertical bars
    col_cover = 40.0 if is_metric else 1.5
    col_bar_y_bot = oy + (85.0 if is_metric else 3.5)
    hook_bend = 150.0 if is_metric else 6.0

    for cx, cw in ((cx1, cw1), (cx2, cw2)):
        c_left_bar = cx - cw / 2.0 + col_cover
        c_right_bar = cx + cw / 2.0 - col_cover
        # Left vertical bar & bend
        draw_line(target, (c_left_bar, col_bar_y_bot), (c_left_bar, col_y_top), layer="Rebar")
        draw_line(target, (c_left_bar, col_bar_y_bot), (c_left_bar - hook_bend, col_bar_y_bot), layer="Rebar")
        # Right vertical bar & bend
        draw_line(target, (c_right_bar, col_bar_y_bot), (c_right_bar, col_y_top), layer="Rebar")
        draw_line(target, (c_right_bar, col_bar_y_bot), (c_right_bar + hook_bend, col_bar_y_bot), layer="Rebar")

    # Column stirrups
    stirrup_sp = (
        combined_footing.column_stirrups.spacing_in
        if combined_footing.column_stirrups
        else (100.0 if is_metric else 4.0)
    )
    stirrup_start_y = oy + (100.0 if is_metric else 4.0)
    n_stirrups = max(1, int((col_y_top - stirrup_start_y) / stirrup_sp))
    for i in range(n_stirrups):
        sy = stirrup_start_y + i * stirrup_sp
        draw_line(target, (col1_left + col_cover, sy), (col1_right - col_cover, sy), layer="Stirrup")
        draw_line(target, (col2_left + col_cover, sy), (col2_right - col_cover, sy), layer="Stirrup")

    # Ld bracket annotation at Column 1 right face
    ld_end_x = col1_right - col_cover + hook_bend
    ld_poly_pts = [
        (col1_right - (20.0 if is_metric else 1.0), thick + oy - (20.0 if is_metric else 1.0)),
        (col1_right, thick + oy),
        (col1_right + (20.0 if is_metric else 1.0), thick + oy - (20.0 if is_metric else 1.0)),
        (col1_right, thick + oy - (20.0 if is_metric else 1.0)),
        (col1_right, thick + oy),
        (col1_right, col_bar_y_bot + (45.0 if is_metric else 1.8)),
        (ld_end_x - (20.0 if is_metric else 1.0), col_bar_y_bot + (45.0 if is_metric else 1.8)),
        (ld_end_x - (20.0 if is_metric else 1.0), col_bar_y_bot + (25.0 if is_metric else 1.0)),
        (ld_end_x, col_bar_y_bot + (45.0 if is_metric else 1.8)),
        (ld_end_x - (20.0 if is_metric else 1.0), col_bar_y_bot + (65.0 if is_metric else 2.6)),
        (ld_end_x - (20.0 if is_metric else 1.0), col_bar_y_bot + (45.0 if is_metric else 1.8)),
    ]
    draw_polyline(target, ld_poly_pts, close=False, layer="Dimension")
    draw_text(
        target,
        "Ld",
        position=(col1_right + (30.0 if is_metric else 1.2), (thick + oy + col_bar_y_bot) / 2.0),
        height=st_sz,
        layer="Text",
    )

    # 8. Multileader Callouts
    bot_rebar_str = f"{_format_rebar_size(bar_dia, is_metric)} @ {_format_dim(bar_spacing, is_metric, include_unit=is_metric)} c/c\nbothways"
    top_rebar_str = f"{_format_rebar_size(top_bar_dia, is_metric)} @ {_format_dim(top_bar_spacing, is_metric, include_unit=is_metric)} c/c\nbothways"

    draw_leader(
        target,
        [
            (cx2 + cw2 / 2.0, oy + (70.0 if is_metric else 2.8)),
            (cx2 + cw2 / 2.0 + 100.0 * s, oy + thick + 100.0 * s),
            (cx2 + cw2 / 2.0 + 200.0 * s, oy + thick + 100.0 * s),
        ],
        text=bot_rebar_str,
        text_height=st_sz,
        layer="Text",
    )
    draw_leader(
        target,
        [
            (x_left + 150.0 * s, oy + thick - (70.0 if is_metric else 2.8)),
            (x_left + 200.0 * s, oy + thick + 150.0 * s),
            (x_left + 300.0 * s, oy + thick + 150.0 * s),
        ],
        text=top_rebar_str,
        text_height=st_sz,
        layer="Text",
    )
    draw_leader(
        target,
        [
            (cx2 + cw2 / 2.0, pl_y + 100.0 * s),
            (cx2 + cw2 / 2.0 + 100.0 * s, pl_y + 200.0 * s),
            (cx2 + cw2 / 2.0 + 200.0 * s, pl_y + 200.0 * s),
        ],
        text=f"Column {_format_dim(cw2, is_metric)}x{_format_dim(cd2, is_metric)}",
        text_height=st_sz,
        layer="Text",
    )

    sub_depth = pcc_thick + soling_thick
    callout_x = x_left + (x_right - x_left) * 0.25
    if pcc_thick > 0:
        pcc_txt = f"{_format_dim(pcc_thick, is_metric, include_unit=True)} thick M10 PCC"
        drop_pcc_y = oy - sub_depth - (120.0 if is_metric else 5.0)
        draw_leader(
            target,
            [
                (callout_x, oy - pcc_thick / 2.0),
                (callout_x, drop_pcc_y),
                (callout_x + (250.0 if is_metric else 10.0), drop_pcc_y),
            ],
            text=pcc_txt,
            text_height=st_sz,
            layer="Text",
        )
    if soling_thick > 0:
        sol_mat = getattr(combined_footing, "soling_material", "brick").lower()
        sol_label = "Flat stone soling" if sol_mat == "stone" else "One flat brick soling"
        sol_txt = f"{_format_dim(soling_thick, is_metric, include_unit=True)} thick {sol_label}"
        drop_sol_y = oy - sub_depth - (270.0 if is_metric else 11.0)
        draw_leader(
            target,
            [
                (callout_x, oy - pcc_thick - soling_thick / 2.0),
                (callout_x, drop_sol_y),
                (callout_x + (250.0 if is_metric else 10.0), drop_sol_y),
            ],
            text=sol_txt,
            text_height=st_sz,
            layer="Text",
        )

    # 9. Dimensions
    dim_y = oy - (sub_depth + (420.0 if is_metric else 17.0))
    draw_dimension(
        target,
        (x_left, dim_y),
        (col1_left, dim_y),
        location=(x_left + (x_left + col1_left) / 2.0, dim_y - 100.0 * s),
        text_override=_format_dim(proj_left - cw1 / 2.0, is_metric),
        layer="Dimension",
    )
    draw_dimension(
        target,
        (col1_left, dim_y),
        (col1_right, dim_y),
        location=(cx1, dim_y - 100.0 * s),
        text_override=_format_dim(cw1, is_metric),
        layer="Dimension",
    )
    draw_dimension(
        target,
        (col1_right, dim_y),
        (col2_left, dim_y),
        location=((col1_right + col2_left) / 2.0, dim_y - 100.0 * s),
        text_override=_format_dim(col_sp - (cw1 + cw2) / 2.0, is_metric),
        layer="Dimension",
    )
    draw_dimension(
        target,
        (col2_left, dim_y),
        (col2_right, dim_y),
        location=(cx2, dim_y - 100.0 * s),
        text_override=_format_dim(cw2, is_metric),
        layer="Dimension",
    )
    draw_dimension(
        target,
        (col2_right, dim_y),
        (x_right, dim_y),
        location=(col2_right + (x_right - col2_right) / 2.0, dim_y - 100.0 * s),
        text_override=_format_dim(proj_right - cw2 / 2.0, is_metric),
        layer="Dimension",
    )

    # Overall length dimension
    draw_dimension(
        target,
        (x_left, dim_y - 200.0 * s),
        (x_right, dim_y - 200.0 * s),
        location=((x_left + x_right) / 2.0, dim_y - 300.0 * s),
        text_override=_format_dim(L, is_metric),
        layer="Dimension",
    )

    # Vertical dimensions
    dim_x = x_left - 300.0 * s
    draw_dimension(
        target,
        (col1_left, oy),
        (col1_left, oy + thick),
        location=(dim_x, oy + thick / 2.0),
        text_override=_format_dim(thick, is_metric),
        layer="Dimension",
    )
    draw_dimension(
        target,
        (col1_left, oy),
        (col1_left, gl_y),
        location=(dim_x - 200.0 * s, gl_y / 2.0),
        text_override=_format_dim(fd, is_metric),
        layer="Dimension",
    )
    draw_dimension(
        target,
        (col1_left, gl_y),
        (col1_left, pl_y),
        location=(dim_x - 400.0 * s, (gl_y + pl_y) / 2.0),
        text_override=_format_dim(pl, is_metric),
        layer="Dimension",
    )

    # View title (placed below all dimensions)
    section_title = title or f"Section of {combined_footing.name} along CX{combined_footing.name}"
    title_x = (x_left + x_right) / 2.0
    title_y = (dim_y - 300.0 * s) - (200.0 if is_metric else 8.0)
    draw_text(
        target,
        section_title,
        position=(title_x, title_y),
        height=title_sz,
        align="middle_center",
        layer="Text",
    )

    level_ext = 1400.0 if is_metric else 50.0
    min_x = min(x_left - 450.0 * s, cx1 - cw1 / 2.0 - level_ext)
    max_x = max(x_right + 450.0 * s, cx2 + cw2 / 2.0 + 1800.0 * s)
    min_y = title_y - title_sz * 1.5
    max_y = pl_y + 1400.0 * s

    return {
        "view": "section",
        "length": L,
        "width": width,
        "thickness": thick,
        "bounding_box": (min_x, min_y, max_x, max_y),
    }


def plan_view(
    target: Any,
    combined_footing: CombinedFootingData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
    scale: Any | None = None,
    unit: Any | None = None,
) -> dict[str, Any]:
    """Draw a plan view of a combined footing."""
    ox, oy = origin
    proj_left = combined_footing.proj_left_in
    proj_right = combined_footing.proj_right_in
    col_sp = combined_footing.col_spacing_in
    L = combined_footing.total_length_in
    B = combined_footing.width_in
    cw1 = combined_footing.col1_width_in
    cd1 = combined_footing.col1_depth_in
    cw2 = combined_footing.col2_width_in
    cd2 = combined_footing.col2_depth_in
    bar_dia = combined_footing.bar_dia_in
    bar_spacing = combined_footing.bar_spacing_in

    scale = scale or getattr(combined_footing, "scale", None)
    unit = unit or getattr(combined_footing, "unit", None)
    if unit is not None:
        from struct_draw.core.units import DrawingUnit
        is_metric = DrawingUnit.from_str(unit).is_metric if isinstance(unit, str) else getattr(unit, "is_metric", True)
    else:
        is_metric = L >= 300.0
    s = 1.0 if is_metric else 1.0 / 25.4

    if is_metric:
        if cw1 < 50.0:
            cw1 = cw1 * 25.4
        if cd1 < 50.0:
            cd1 = cd1 * 25.4
        if cw2 < 50.0:
            cw2 = cw2 * 25.4
        if cd2 < 50.0:
            cd2 = cd2 * 25.4

    if scale is not None or unit is not None:
        from struct_draw.core.units import DrawingScale, DrawingUnit, SCALE_1_25, SCALE_1_IN
        from struct_draw.style.annotation_config import DEFAULT_ANNOTATION_CONFIG
        d_unit = unit or (DrawingUnit.MM if is_metric else DrawingUnit.IN)
        d_scale = scale or (SCALE_1_25 if is_metric else SCALE_1_IN)
        txt_sz = DEFAULT_ANNOTATION_CONFIG.text_height(d_scale, d_unit)
        st_sz = DEFAULT_ANNOTATION_CONFIG.dim_text_height(d_scale, d_unit)
    else:
        txt_sz = 100.0 * s
        st_sz = 80.0 * s

    cx1 = ox
    cx2 = ox + col_sp
    x_left = cx1 - proj_left
    x_right = cx2 + proj_right
    y_bot = oy - B / 2.0
    y_top = oy + B / 2.0

    # 1. Footing pad outer boundary
    draw_rectangle(
        target,
        origin=(x_left, y_bot),
        width=x_right - x_left,
        height=y_top - y_bot,
        layer="Foundation",
    )

    # 2. Columns in plan view
    draw_rectangle(
        target,
        origin=(cx1 - cw1 / 2.0, oy - cd1 / 2.0),
        width=cw1,
        height=cd1,
        layer="Column",
    )
    draw_rectangle(
        target,
        origin=(cx2 - cw2 / 2.0, oy - cd2 / 2.0),
        width=cw2,
        height=cd2,
        layer="Column",
    )

    # 3. Centerlines
    draw_line(
        target,
        (x_left - 300.0 * s, oy),
        (x_right + 300.0 * s, oy),
        layer="CEN",
    )
    draw_line(
        target,
        (cx1, y_bot - 300.0 * s),
        (cx1, y_top + 300.0 * s),
        layer="CEN",
    )
    draw_line(
        target,
        (cx2, y_bot - 300.0 * s),
        (cx2, y_top + 300.0 * s),
        layer="CEN",
    )

    # Axis Labels
    draw_text(
        target,
        "CX1",
        position=(cx1 - 75.0 * s, y_top + 350.0 * s),
        height=st_sz,
        layer="Text",
    )
    draw_text(
        target,
        "CX2",
        position=(cx2 - 75.0 * s, y_top + 350.0 * s),
        height=st_sz,
        layer="Text",
    )

    # Footing Label
    draw_text(
        target,
        combined_footing.name,
        position=(x_right - 500.0 * s, y_top - 500.0 * s),
        height=txt_sz,
        layer="Text",
    )

    # 4. Rebar representations in Plan View
    rb_offset = 150.0 * s
    draw_polyline(
        target,
        [
            (x_left + 60.0 * s, y_bot + rb_offset + 100.0 * s),
            (x_left + 60.0 * s, y_bot + rb_offset),
            (x_right - 60.0 * s, y_bot + rb_offset),
            (x_right - 60.0 * s, y_bot + rb_offset + 100.0 * s),
        ],
        close=False,
        layer="Rebar",
    )
    dim_reb = draw_dimension(
        target,
        (x_left + 60.0 * s, y_bot + rb_offset),
        (x_right - 60.0 * s, y_bot + rb_offset),
        location=((x_left + x_right) / 2.0, y_bot + rb_offset - 60.0 * s),
        layer="Dimension",
    )
    dim_reb.text = f"Bottom Bar: {_format_rebar_size(bar_dia, is_metric)} @ {_format_dim(bar_spacing, is_metric, include_unit=is_metric)} c/c"

    # Transverse rebar indicator
    draw_polyline(
        target,
        [
            (cx1 + rb_offset + 100.0 * s, y_bot + 60.0 * s),
            (cx1 + rb_offset, y_bot + 60.0 * s),
            (cx1 + rb_offset, y_top - 60.0 * s),
            (cx1 + rb_offset + 100.0 * s, y_top - 60.0 * s),
        ],
        close=False,
        layer="Rebar",
    )

    # 5. Dimensions for Plan View
    dim_y = y_bot - 200.0 * s
    draw_dimension(
        target,
        (x_left, dim_y),
        (cx1, dim_y),
        location=(x_left + proj_left / 2.0, dim_y - 100.0 * s),
        text_override=_format_dim(proj_left, is_metric),
        layer="Dimension",
    )
    draw_dimension(
        target,
        (cx1, dim_y),
        (cx2, dim_y),
        location=((cx1 + cx2) / 2.0, dim_y - 100.0 * s),
        text_override=_format_dim(col_sp, is_metric),
        layer="Dimension",
    )
    draw_dimension(
        target,
        (cx2, dim_y),
        (x_right, dim_y),
        location=(cx2 + proj_right / 2.0, dim_y - 100.0 * s),
        text_override=_format_dim(proj_right, is_metric),
        layer="Dimension",
    )
    draw_dimension(
        target,
        (x_left, dim_y - 200.0 * s),
        (x_right, dim_y - 200.0 * s),
        location=((x_left + x_right) / 2.0, dim_y - 300.0 * s),
        text_override=_format_dim(L, is_metric),
        layer="Dimension",
    )

    # Vertical dimensions along left
    dim_x = x_left - 200.0 * s
    draw_dimension(
        target,
        (dim_x, y_bot),
        (dim_x, oy),
        location=(dim_x - 100.0 * s, oy - B / 4.0),
        text_override=_format_dim(B / 2.0, is_metric),
        layer="Dimension",
    )
    draw_dimension(
        target,
        (dim_x, oy),
        (dim_x, y_top),
        location=(dim_x - 100.0 * s, oy + B / 4.0),
        text_override=_format_dim(B / 2.0, is_metric),
        layer="Dimension",
    )
    draw_dimension(
        target,
        (dim_x - 200.0 * s, y_bot),
        (dim_x - 200.0 * s, y_top),
        location=(dim_x - 300.0 * s, oy),
        text_override=_format_dim(B, is_metric),
        layer="Dimension",
    )

    # Title text below plan
    plan_title = title or f"Plan of {combined_footing.name}"
    draw_text(
        target,
        plan_title,
        position=((x_left + x_right) / 2.0, y_bot - 450.0 * s),
        height=txt_sz,
        align="middle_center",
        layer="Text",
    )

    min_x = x_left - 450.0 * s
    max_x = x_right + 300.0 * s
    min_y = y_bot - 650.0 * s - txt_sz * 1.5
    max_y = y_top + 250.0 * s

    return {
        "view": "plan",
        "length": L,
        "width": B,
        "bounding_box": (min_x, min_y, max_x, max_y),
    }


__all__ = ["section_view", "plan_view"]
