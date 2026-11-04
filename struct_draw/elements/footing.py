"""struct_draw.elements.footing — Plan + section views for spread footings.

This module implements detailed, production-ready structural drawing functions
for spread / sloped footings based on the reference standard in
``references/footing.py``.

Key features:
* Accurate geometry for sloped footings with pedestals/ledges.
* PCC (Plain Cement Concrete) and Flat Brick Soling sub-base layers.
* Plinth Beam and Foundation Beam cross-sections.
* Column stem elevation with top break line.
* Ground Level (GL) and Plinth Level (PL) markers.
* Complete reinforcement detailing:
  - Bottom footing rebar with vertical end hooks and transverse rebar dots.
  - Column longitudinal vertical bars extending down with horizontal Ld bends into footing.
  - Development length "Ld" bracket annotation.
  - Column stirrups / rings.
* Multileader callouts for rebar, column, stirrups, beams, PCC, and soling.
* Plan view with footing, pedestal, column, diagonal slope lines, centerline, and rebar representation.
"""

from __future__ import annotations

from typing import Any, Sequence

from struct_draw.core.composite import (
    draw_beam_section,
    draw_break_line,
    draw_dimension,
    draw_hatch,
    draw_leader,
    draw_level_marker,
    draw_line,
    draw_polyline,
    draw_rebar_circle,
    draw_section_cut_symbol,
    draw_stirrup_hooked,
    draw_text,
)
from struct_draw.core.data import FootingData, IsolatedFootingData, Rebar
from struct_draw.core.primitives import draw_rectangle
from struct_draw.core.units import format_length


def _clean_text(txt: str) -> str:
    """Replace non-rendering unicode symbols with standard CAD text."""
    if not txt:
        return ""
    return txt.replace("φ", "mm dia").replace("Φ", "mm dia").replace("ϕ", "mm dia")


def _format_rebar_size(bar_dia_in: float, is_metric: bool = False, bar_size_str: str | None = None) -> str:
    """Format rebar size/diameter string."""
    if bar_size_str:
        clean = _clean_text(bar_size_str)
        if is_metric and clean.startswith("#"):
            try:
                sz_num = int(clean[1:])
                dia_mm = round(sz_num * 25.4 / 8.0)
                return f"{clean} ({dia_mm} mm)"
            except ValueError:
                return clean
        return clean
    if is_metric:
        dia_mm = round(bar_dia_in * 25.4) if bar_dia_in < 3.0 else round(bar_dia_in)
        return f"{dia_mm}mm dia"
    else:
        dia_in = bar_dia_in / 25.4 if bar_dia_in >= 4.0 else bar_dia_in
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
            if abs(dia_in - val) < 0.05:
                return size
        if dia_in.is_integer():
            return f'{int(dia_in)}"'
        return f'{dia_in:.2f}"'


def _format_dim(val: float, is_metric: bool = False, include_unit: bool = False) -> str:
    """Format dimension value string."""
    if is_metric or val >= 300.0:
        if include_unit:
            return f"{int(val)}mm" if val.is_integer() else f"{val:.1f}mm"
        return f"{int(val)}" if val.is_integer() else f"{val:.1f}"
    if val.is_integer():
        return f'{int(val)}"'
    return f'{val:.1f}"'


def bar_off_y(footing: IsolatedFootingData) -> float:
    """The vertical offset of a footing bar from the concrete face."""
    return footing.cover_in + footing.bar_dia_in / 2.0


def section_view(
    target: Any,
    footing: IsolatedFootingData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
    scale: Any | None = None,
    unit: Any | None = None,
) -> dict[str, Any]:
    """Draw a full cross-section of ``footing`` matching references/footing.py."""
    ox, oy = origin
    L = footing.length_in
    B = footing.width_in
    t_mid = footing.mid_thickness_in
    t_edge = footing.edge_thickness_in
    cw = footing.column_width_in
    cd = footing.column_depth_in
    ch = footing.column_height_in
    fd = footing.footing_depth_in
    pl = footing.plinth_height_in
    cover = footing.cover_in
    bar_dia = footing.bar_dia_in
    spacing = footing.bar_spacing_in
    Ld = footing.development_length_in
    ledge = footing.ledge_in
    pcc_thick = footing.pcc_thickness_in
    soling_thick = footing.soling_thickness_in

    scale = scale or getattr(footing, "scale", None)
    unit = unit or getattr(footing, "unit", None)
    if unit is not None:
        from struct_draw.core.units import DrawingUnit
        is_metric = DrawingUnit.from_str(unit).is_metric if isinstance(unit, str) else getattr(unit, "is_metric", True)
    else:
        is_metric = L >= 300.0

    if is_metric:
        if cw < 50.0:
            cw = cw * 25.4
        if cd < 50.0:
            cd = cd * 25.4
        if ledge < 10.0:
            ledge = ledge * 25.4
        if pcc_thick < 10.0 and pcc_thick > 0:
            pcc_thick = pcc_thick * 25.4
        if soling_thick < 10.0 and soling_thick > 0:
            soling_thick = soling_thick * 25.4
        if Ld < 50.0:
            Ld = Ld * 25.4
        if ch < 150.0:
            ch = ch * 25.4

    # Beam dimensions
    pb_w = footing.plinth_beam_width_in or (230.0 if is_metric else 9.0)
    pb_h = footing.plinth_beam_depth_in or (350.0 if is_metric else 14.0)
    fb_w = footing.foundation_beam_width_in or (230.0 if is_metric else 9.0)
    fb_h = footing.foundation_beam_depth_in or (300.0 if is_metric else 12.0)

    # Scale helpers for drawing features
    s_ext = 400.0 if is_metric else 16.0
    if scale is not None or unit is not None:
        from struct_draw.core.units import DrawingScale, DrawingUnit, SCALE_1_25, SCALE_1_IN
        from struct_draw.style.annotation_config import DEFAULT_ANNOTATION_CONFIG
        d_unit = unit or (DrawingUnit.MM if is_metric else DrawingUnit.IN)
        d_scale = scale or (SCALE_1_25 if is_metric else SCALE_1_IN)
        txt_sz = DEFAULT_ANNOTATION_CONFIG.text_height(d_scale, d_unit)
        hdr_txt_sz = DEFAULT_ANNOTATION_CONFIG.text_height(d_scale, d_unit)
        st_sz = DEFAULT_ANNOTATION_CONFIG.dim_text_height(d_scale, d_unit)
        arr_sz = DEFAULT_ANNOTATION_CONFIG.arrow_size(d_scale, d_unit)
    else:
        txt_sz = 100.0 if is_metric else 4.0
        hdr_txt_sz = 100.0 if is_metric else 4.0
        st_sz = 80.0 if is_metric else 3.0
        arr_sz = 50.0 if is_metric else 2.0
    dot_r = 7.0 if is_metric else max(bar_dia / 2.0, 0.25)
    hook_h = 80.0 if is_metric else 3.0
    end_margin = cover if cover > 0 else (75.0 if is_metric else 3.0)

    # 1. Foundation Slab + Sloped Edges + Pedestal Ledge
    foundation_pts = [
        (-L / 2.0 + ox, 0.0 + oy),
        (L / 2.0 + ox, 0.0 + oy),
        (L / 2.0 + ox, t_edge + oy),
        (cw / 2.0 + ledge + ox, t_mid + oy),
        (cw / 2.0 + ox, t_mid + oy),
        (-cw / 2.0 + ox, t_mid + oy),
        (-cw / 2.0 - ledge + ox, t_mid + oy),
        (-L / 2.0 + ox, t_edge + oy),
        (-L / 2.0 + ox, 0.0 + oy),
    ]
    draw_polyline(target, foundation_pts, close=True, layer="Foundation")

    # 2. PCC Layer
    if pcc_thick > 0:
        pcc_pts = [
            (-L / 2.0 + ox, 0.0 + oy),
            (-L / 2.0 + ox, -pcc_thick + oy),
            (L / 2.0 + ox, -pcc_thick + oy),
            (L / 2.0 + ox, 0.0 + oy),
        ]
        draw_polyline(target, pcc_pts, close=True, layer="Foundation")
        draw_hatch(
            target,
            paths=[{"type": "polyline", "points": pcc_pts, "is_closed": True}],
            pattern="AR-CONC",
            scale=15.0 if is_metric else 0.6,
            layer="HATCH",
        )

    # 3. Soling Layer (Brick or Stone)
    if soling_thick > 0:
        sol_pts = [
            (-L / 2.0 + ox, -pcc_thick + oy),
            (-L / 2.0 + ox, -pcc_thick - soling_thick + oy),
            (L / 2.0 + ox, -pcc_thick - soling_thick + oy),
            (L / 2.0 + ox, -pcc_thick + oy),
        ]
        draw_polyline(target, sol_pts, close=True, layer="Foundation")
        sol_mat = getattr(footing, "soling_material", "brick").lower()
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

    # 4. Column Stem
    col_y_top = fd + pl + s_ext + oy
    col_pts = [
        (-cw / 2.0 + ox, t_mid + oy),
        (-cw / 2.0 + ox, col_y_top),
        (cw / 2.0 + ox, col_y_top),
        (cw / 2.0 + ox, t_mid + oy),
    ]
    draw_polyline(target, col_pts, close=False, layer="Column")

    # 5. Break Line at Top of Column
    bp_x = cw / 2.0 + (100.0 if is_metric else 4.0)
    zigzag = 50.0 if is_metric else 2.0
    break_line_pts = [
        (-bp_x + ox, col_y_top),
        (-zigzag * 0.6 + ox, col_y_top),
        (0.0 + ox, col_y_top + zigzag),
        (0.0 + ox, col_y_top - zigzag),
        (zigzag * 0.6 + ox, col_y_top),
        (bp_x + ox, col_y_top),
    ]
    draw_polyline(target, break_line_pts, close=False, layer="Column")

    # 6. Level Lines: Ground Level (GL) and Plinth Level (PL)
    gl_y = fd + oy
    pl_y = fd + pl + oy
    dim_off = (DEFAULT_ANNOTATION_CONFIG.dim_offset(d_scale, d_unit) if (scale is not None or unit is not None) else 300.0)
    level_ext = max(1800.0 if is_metric else 72.0, dim_off * 4.5)
    p_GL = (-cw / 2.0 + ox, gl_y)
    p_PL = (-cw / 2.0 + ox, pl_y)
    draw_line(target, p_GL, (p_GL[0] - level_ext, p_GL[1]), layer="Level")
    draw_line(target, p_PL, (p_PL[0] - level_ext, p_PL[1]), layer="Level")

    txt_x = p_GL[0] - level_ext + (50.0 if is_metric else 2.0)
    draw_text(target, "Ground Lvl.", position=(txt_x, p_GL[1] + st_sz * 0.25), height=st_sz, align="bottom_left", layer="Text")
    draw_text(target, "Plinth Lvl.", position=(txt_x, p_PL[1] + st_sz * 0.25), height=st_sz, align="bottom_left", layer="Text")

    # 7. Rebar Details
    # Bottom main rebar line with hooks
    rebar_y = (cover + bar_dia / 2.0) + oy
    p_rebar_left = -L / 2.0 + end_margin + ox
    p_rebar_right = L / 2.0 - end_margin + ox

    bot_rebar_pts = [
        (p_rebar_left, rebar_y + hook_h),
        (p_rebar_left, rebar_y),
        (p_rebar_right, rebar_y),
        (p_rebar_right, rebar_y + hook_h),
    ]
    draw_polyline(target, bot_rebar_pts, close=False, layer="Rebar")

    # Transverse rebar circles
    n_bot_bar = int((p_rebar_right - p_rebar_left) / spacing)
    if n_bot_bar > 0:
        actual_sp = (p_rebar_right - p_rebar_left - 2 * dot_r) / max(1, n_bot_bar)
        for i in range(n_bot_bar + 1):
            cx = p_rebar_left + dot_r + i * actual_sp
            cy = rebar_y + dot_r
            draw_rebar_circle(target, (cx, cy), diameter=dot_r * 2.0, layer="Rebar_hatch")

    # Column longitudinal vertical bars with horizontal Ld hooks
    col_cover = 50.0 if is_metric else cover
    col_left_bar_x = -cw / 2.0 + col_cover + ox
    col_right_bar_x = cw / 2.0 - col_cover + ox
    col_bar_y_bot = rebar_y + dot_r * 2.0

    # Vertical lines
    draw_line(target, (ox, col_bar_y_bot), (ox, col_y_top), layer="Rebar")
    draw_line(target, (col_left_bar_x, col_bar_y_bot), (col_left_bar_x, col_y_top), layer="Rebar")
    draw_line(target, (col_right_bar_x, col_bar_y_bot), (col_right_bar_x, col_y_top), layer="Rebar")

    # Horizontal Ld hooks in footing
    pcf1_x = -L * 0.35 + ox
    pcf2_x = L * 0.35 + ox
    draw_line(target, (pcf1_x, col_bar_y_bot), (pcf2_x, col_bar_y_bot), layer="Rebar")
    draw_line(target, (pcf1_x, col_bar_y_bot), (pcf1_x, col_bar_y_bot + hook_h), layer="Rebar")
    draw_line(target, (pcf2_x, col_bar_y_bot), (pcf2_x, col_bar_y_bot + hook_h), layer="Rebar")

    # Ld annotation bracket (starts at right column face and ends at right hook end)
    ld_poly_pts = [
        (cw / 2.0 + ox, t_mid + oy - (50.0 if is_metric else 2.0)),
        (cw / 2.0 - (20.0 if is_metric else 1.0) + ox, t_mid + oy - (50.0 if is_metric else 2.0)),
        (cw / 2.0 + ox, t_mid + oy),
        (cw / 2.0 + (20.0 if is_metric else 1.0) + ox, t_mid + oy - (50.0 if is_metric else 2.0)),
        (cw / 2.0 + ox, t_mid + oy - (50.0 if is_metric else 2.0)),
        (cw / 2.0 + ox, col_bar_y_bot + (45.0 if is_metric else 1.8)),
        (pcf2_x - (50.0 if is_metric else 2.0), col_bar_y_bot + (45.0 if is_metric else 1.8)),
        (pcf2_x - (50.0 if is_metric else 2.0), col_bar_y_bot + (25.0 if is_metric else 1.0)),
        (pcf2_x, col_bar_y_bot + (45.0 if is_metric else 1.8)),
        (pcf2_x - (50.0 if is_metric else 2.0), col_bar_y_bot + (65.0 if is_metric else 2.6)),
        (pcf2_x - (50.0 if is_metric else 2.0), col_bar_y_bot + (45.0 if is_metric else 1.8)),
    ]
    draw_polyline(target, ld_poly_pts, close=False, layer="Dimension")
    draw_text(
        target,
        "Ld",
        position=(cw / 2.0 + (30.0 if is_metric else 1.2) + ox, (t_mid + oy + col_bar_y_bot) / 2.0),
        height=st_sz,
        layer="Text",
    )

    # Column stirrups (only draw if explicitly defined in footing data)
    has_col_stirrups = bool(footing.column_stirrups and footing.column_stirrups.spacing_in > 0)
    if has_col_stirrups:
        st_sp = footing.column_stirrups.spacing_in
        st_y0 = t_mid + (100.0 if is_metric else 4.0) + oy
        n_st = int((col_y_top - st_y0) / st_sp)
        for i in range(max(1, n_st)):
            sy = st_y0 + i * st_sp
            if sy < col_y_top:
                draw_line(target, (col_left_bar_x, sy), (col_right_bar_x, sy), layer="Stirrup")

    # 8. Beam Cross-Section Blocks
    if pb_w > 0 and pb_h > 0:
        draw_beam_section(
            target,
            center_x=ox,
            top_y=fd + pl + oy,
            width=pb_w,
            height=pb_h,
            is_metric=is_metric,
        )

    if fb_w > 0 and fb_h > 0:
        draw_beam_section(
            target,
            center_x=ox,
            top_y=t_mid + fb_h + oy,
            width=fb_w,
            height=fb_h,
            is_metric=is_metric,
        )

    # 9. Leaders / Callouts
    cov_note = f"CLEAR COVER {footing.cover_in:g}mm" if is_metric else f'CLEAR COVER {footing.cover_in:g}"'
    sp_str = format_length(spacing, is_metric)
    bar_sz_name = getattr(footing, "bar_size", None)
    rebar_label = _format_rebar_size(bar_dia, is_metric, bar_sz_name)
    text_bar = f"{rebar_label} @ {sp_str} c/c \nbothways ({cov_note})"
    draw_leader(
        target,
        [
            (cw / 2.0 + ox, rebar_y),
            (cw / 2.0 + (150.0 if is_metric else 6.0) + ox, t_mid + (100.0 if is_metric else 4.0) + oy),
            (cw / 2.0 + (300.0 if is_metric else 12.0) + ox, t_mid + (100.0 if is_metric else 4.0) + oy),
        ],
        text=text_bar,
        text_height=st_sz,
        layer="Text",
    )

    text_col = f"Column {_format_dim(cw, is_metric)}x{_format_dim(cd, is_metric)}"
    draw_leader(
        target,
        [
            (cw / 2.0 + ox, fd + pl + (200.0 if is_metric else 8.0) + oy),
            (cw / 2.0 + (100.0 if is_metric else 4.0) + ox, fd + pl + (300.0 if is_metric else 12.0) + oy),
            (cw / 2.0 + (250.0 if is_metric else 10.0) + ox, fd + pl + (300.0 if is_metric else 12.0) + oy),
        ],
        text=text_col,
        text_height=st_sz,
        layer="Text",
    )

    if has_col_stirrups:
        st_dia_raw = footing.column_stirrups.size or "#3"
        st_dia_str = _clean_text(st_dia_raw)
        st_sp_str = format_length(st_sp, is_metric)
        text_ring = f"{st_dia_str} @ {st_sp_str} c/c \ncolumn stirrups"
        draw_leader(
            target,
            [
                (col_left_bar_x + (50.0 if is_metric else 2.0), t_mid + (700.0 if is_metric else 28.0) + oy),
                (cw / 2.0 + (100.0 if is_metric else 4.0) + ox, t_mid + (900.0 if is_metric else 36.0) + oy),
                (cw / 2.0 + (250.0 if is_metric else 10.0) + ox, t_mid + (900.0 if is_metric else 36.0) + oy),
            ],
            text=text_ring,
            text_height=st_sz,
            layer="Text",
        )

    if fb_w > 0 and fb_h > 0:
        text_fb = f"Foundation Beam \n{_format_dim(fb_w, is_metric)}x{_format_dim(fb_h, is_metric)}"
        draw_leader(
            target,
            [
                (fb_w / 2.0 + ox, t_mid + fb_h / 2.0 + oy),
                (cw / 2.0 + (100.0 if is_metric else 4.0) + ox, t_mid + (500.0 if is_metric else 20.0) + oy),
                (cw / 2.0 + (250.0 if is_metric else 10.0) + ox, t_mid + (500.0 if is_metric else 20.0) + oy),
            ],
            text=text_fb,
            text_height=st_sz,
            layer="Text",
        )

    if pb_w > 0 and pb_h > 0:
        text_pb = f"Plinth Beam \n{_format_dim(pb_w, is_metric)}x{_format_dim(pb_h, is_metric)}"
        draw_leader(
            target,
            [
                (pb_w / 2.0 + ox, fd + pl - pb_h / 2.0 + oy),
                (cw / 2.0 + (150.0 if is_metric else 6.0) + ox, fd + pl + oy),
                (cw / 2.0 + (300.0 if is_metric else 12.0) + ox, fd + pl + oy),
            ],
            text=text_pb,
            text_height=st_sz,
            layer="Text",
        )

    if pcc_thick > 0:
        pcc_y = -pcc_thick / 2.0 + oy
        pcc_x = L / 3.0 + ox
        draw_leader(
            target,
            [
                (pcc_x, pcc_y),
                (pcc_x, -pcc_thick - soling_thick - (150.0 if is_metric else 6.0) + oy),
                (pcc_x + (300.0 if is_metric else 12.0), -pcc_thick - soling_thick - (150.0 if is_metric else 6.0) + oy),
            ],
            text=f"{_format_dim(pcc_thick, is_metric, include_unit=True)} thick M10 PCC",
            text_height=st_sz,
            layer="Text",
        )

    if soling_thick > 0:
        sol_y = -pcc_thick - soling_thick / 2.0 + oy
        sol_x = L / 3.0 + ox
        sol_mat = getattr(footing, "soling_material", "brick").lower()
        sol_label = "Flat stone soling" if sol_mat == "stone" else "One flat brick soling"
        draw_leader(
            target,
            [
                (sol_x, sol_y),
                (sol_x, -pcc_thick - soling_thick - (300.0 if is_metric else 12.0) + oy),
                (sol_x + (300.0 if is_metric else 12.0), -pcc_thick - soling_thick - (300.0 if is_metric else 12.0) + oy),
            ],
            text=f"{_format_dim(soling_thick, is_metric, include_unit=True)} thick {sol_label}",
            text_height=st_sz,
            layer="Text",
        )

    # 10. Dimensions
    s = 1.0 if is_metric else 1.0 / 25.4
    # dim_fb: Footing Length L
    draw_dimension(
        target,
        (-L / 2.0 + ox, 0.0 + oy),
        (L / 2.0 + ox, 0.0 + oy),
        location=(ox, -300.0 * s + oy),
        text_override=_format_dim(L, is_metric),
        layer="Dimension",
    )
    # dim_et: Edge Thickness t_edge
    draw_dimension(
        target,
        (-L / 2.0 + ox, 0.0 + oy),
        (-L / 2.0 + ox, t_edge + oy),
        location=(-L / 2.0 - 200.0 * s + ox, t_edge / 2.0 + oy),
        text_override=_format_dim(t_edge, is_metric),
        layer="Dimension",
    )
    # dim_mt: Mid Thickness t_mid
    draw_dimension(
        target,
        (-cw / 2.0 + ox, 0.0 + oy),
        (-cw / 2.0 + ox, t_mid + oy),
        location=(-L / 2.0 - 400.0 * s + ox, t_mid / 2.0 + oy),
        text_override=_format_dim(t_mid, is_metric),
        layer="Dimension",
    )
    # dim_fd: Footing Depth fd
    draw_dimension(
        target,
        (-cw / 2.0 + ox, 0.0 + oy),
        (-cw / 2.0 + ox, fd + oy),
        location=(-L / 2.0 - 600.0 * s + ox, fd / 2.0 + oy),
        text_override=_format_dim(fd, is_metric),
        layer="Dimension",
    )
    # dim_pl: Plinth Height pl
    draw_dimension(
        target,
        (-cw / 2.0 + ox, fd + oy),
        (-cw / 2.0 + ox, fd + pl + oy),
        location=(-cw / 2.0 - 1000.0 * s + ox, fd + pl / 2.0 + oy),
        text_override=_format_dim(pl, is_metric),
        layer="Dimension",
    )
    # ledge_dim: Ledge / Pedestal ledge width
    draw_dimension(
        target,
        (-cw / 2.0 - ledge + ox, t_mid + oy),
        (-cw / 2.0 + ox, t_mid + oy),
        location=(-cw / 2.0 - ledge / 2.0 + ox, t_mid + 100.0 * s + oy),
        text_override=_format_dim(ledge, is_metric),
        layer="Dimension",
    )

    # 11. Section Title
    foot_id = footing.name[1:] if footing.name.startswith("F") else footing.name
    if title is None:
        title = f"Section of F{foot_id} at X{foot_id}"
    draw_text(
        target,
        title,
        position=(ox, -1000.0 * s + oy),
        height=txt_sz,
        align="middle_center",
        layer="Text",
    )

    min_x = min(-cw / 2.0 - level_ext, -L / 2.0 - 700.0 * s) + ox
    max_x = max(L / 2.0 + 400.0 * s, cw / 2.0 + 2000.0 * s) + ox
    min_y = min(-pcc_thick - soling_thick, -1000.0 * s - txt_sz * 2.0) + oy
    max_y = col_y_top + 200.0 * s

    return {
        "origin": (ox, oy),
        "column_top": col_y_top,
        "ground_level": gl_y,
        "plinth_level": pl_y,
        "footing_length": L,
        "footing_width": B,
        "bounding_box": (min_x, min_y, max_x, max_y),
    }


def plan_view(
    target: Any,
    footing: IsolatedFootingData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
    scale: Any | None = None,
    unit: Any | None = None,
) -> dict[str, Any]:
    """Draw the plan view of ``footing`` matching references/footing.py."""
    pcx, pcy = origin
    L = footing.length_in
    B = footing.width_in
    cw = footing.column_width_in
    cd = footing.column_depth_in
    ledge = footing.ledge_in
    bar_dia = footing.bar_dia_in
    spacing = footing.bar_spacing_in
    foot_id = footing.name[1:] if footing.name.startswith("F") else footing.name

    scale = scale or getattr(footing, "scale", None)
    unit = unit or getattr(footing, "unit", None)
    if unit is not None:
        from struct_draw.core.units import DrawingUnit
        is_metric = DrawingUnit.from_str(unit).is_metric if isinstance(unit, str) else getattr(unit, "is_metric", True)
    else:
        is_metric = L >= 300.0

    if is_metric:
        if cw < 50.0:
            cw = cw * 25.4
        if cd < 50.0:
            cd = cd * 25.4
        if ledge < 10.0:
            ledge = ledge * 25.4

    # Scale helpers
    if scale is not None or unit is not None:
        from struct_draw.core.units import DrawingScale, DrawingUnit, SCALE_1_25, SCALE_1_IN
        from struct_draw.style.annotation_config import DEFAULT_ANNOTATION_CONFIG
        d_unit = unit or (DrawingUnit.MM if is_metric else DrawingUnit.IN)
        d_scale = scale or (SCALE_1_25 if is_metric else SCALE_1_IN)
        txt_sz = DEFAULT_ANNOTATION_CONFIG.text_height(d_scale, d_unit)
        sub_txt_sz = DEFAULT_ANNOTATION_CONFIG.dim_text_height(d_scale, d_unit)
    else:
        txt_sz = 100.0 if is_metric else 4.0
        sub_txt_sz = 80.0 if is_metric else 3.0
    hk = 100.0 if is_metric else 4.0
    cen_ext = 500.0 if is_metric else 20.0

    # 1. Rectangles
    # Column
    col_1 = (pcx - cw / 2.0, pcy - cd / 2.0)
    col_2 = (pcx + cw / 2.0, pcy + cd / 2.0)
    draw_rectangle(target, origin=col_1, width=cw, height=cd, layer="Column")

    # Pedestal / Ledge
    ledge_1 = (pcx - cw / 2.0 - ledge, pcy - cd / 2.0 - ledge)
    ledge_2 = (pcx + cw / 2.0 + ledge, pcy + cd / 2.0 + ledge)
    draw_rectangle(target, origin=ledge_1, width=cw + 2.0 * ledge, height=cd + 2.0 * ledge, layer="Foundation")

    # Footing Outer Rectangle
    foot_1 = (pcx - L / 2.0, pcy - B / 2.0)
    foot_2 = (pcx + L / 2.0, pcy + B / 2.0)
    draw_rectangle(target, origin=foot_1, width=L, height=B, layer="Foundation")

    # 2. Diagonal Corner Slope Lines
    draw_line(target, ledge_1, foot_1, layer="Foundation")
    draw_line(target, (ledge_2[0], ledge_1[1]), (foot_2[0], foot_1[1]), layer="Foundation")
    draw_line(target, (ledge_1[0], ledge_2[1]), (foot_1[0], foot_2[1]), layer="Foundation")
    draw_line(target, ledge_2, foot_2, layer="Foundation")

    # 3. Rebar Representation in Plan
    s = 1.0 if is_metric else 1.0 / 25.4
    off_x = 60.0 * s
    off_y = 150.0 * s

    # Horizontal rebar with hooks along bottom edge
    p_h1 = (foot_1[0] + off_x, foot_1[1] + off_y)
    p_h2 = (foot_2[0] - off_x, foot_1[1] + off_y)
    rebar_h_pts = [
        (p_h1[0], p_h1[1] + hk),
        p_h1,
        p_h2,
        (p_h2[0], p_h2[1] + hk),
    ]
    draw_polyline(target, rebar_h_pts, close=False, layer="Rebar")
    draw_dimension(
        target,
        p_h1,
        p_h2,
        location=(pcx, foot_1[1] + 350.0 * s),
        text_override=f"{_format_rebar_size(bar_dia, is_metric, getattr(footing, 'bar_size', None))} @ {format_length(spacing, is_metric)} c/c",
        layer="Dimension",
    )

    # Vertical rebar with hooks along left edge
    p_v1 = (foot_1[0] + off_y, foot_1[1] + off_x)
    p_v2 = (foot_1[0] + off_y, foot_2[1] - off_x)
    rebar_v_pts = [
        (p_v1[0] + hk, p_v1[1]),
        p_v1,
        p_v2,
        (p_v2[0] + hk, p_v2[1]),
    ]
    draw_polyline(target, rebar_v_pts, close=False, layer="Rebar")
    draw_dimension(
        target,
        p_v1,
        p_v2,
        location=(foot_1[0] + 350.0 * s, pcy),
        text_override=f"{_format_rebar_size(bar_dia, is_metric, getattr(footing, 'bar_size', None))} @ {format_length(spacing, is_metric)} c/c",
        layer="Dimension",
    )

    # 4. Centerline Axis & Section Cut
    p_slabel = (foot_1[0] - cen_ext, pcy)
    p_slabel_r = (foot_2[0] + cen_ext, pcy)
    sec_cut_left = [
        (pcx, pcy),
        (p_slabel[0] - 75.0 * s, pcy),
        (p_slabel[0] - 75.0 * s, pcy + 75.0 * s),
        (p_slabel[0], pcy + 75.0 * s),
    ]
    sec_cut_right = [
        (pcx, pcy),
        (p_slabel_r[0] + 75.0 * s, pcy),
        (p_slabel_r[0] + 75.0 * s, pcy + 75.0 * s),
        (p_slabel_r[0], pcy + 75.0 * s),
    ]
    draw_polyline(target, sec_cut_left, close=False, layer="CEN")
    draw_polyline(target, sec_cut_right, close=False, layer="CEN")

    draw_text(
        target,
        f"X{foot_id}",
        position=(p_slabel[0] - 75.0 * s, pcy + 90.0 * s),
        height=80.0 * s,
        layer="Text",
    )
    draw_text(
        target,
        f"F{foot_id}",
        position=(ledge_2[0] - 10.0 * s, ledge_2[1] + 200.0 * s),
        height=90.0 * s,
        layer="Text",
    )

    # 5. Dimensions
    # Footing Length L
    draw_dimension(
        target,
        foot_1,
        (foot_2[0], foot_1[1]),
        location=(pcx, foot_1[1] - 200.0 * s),
        text_override=_format_dim(L, is_metric),
        layer="Dimension",
    )
    # Footing Width B
    draw_dimension(
        target,
        foot_1,
        (foot_1[0], foot_2[1]),
        location=(foot_1[0] - 200.0 * s, pcy),
        text_override=_format_dim(B, is_metric),
        layer="Dimension",
    )
    # Column Depth cd
    draw_dimension(
        target,
        col_2,
        (col_2[0], col_1[1]),
        location=(col_2[0] + 200.0 * s, pcy),
        text_override=_format_dim(cd, is_metric),
        layer="Dimension",
    )
    # Pedestal Depth cd + 2*ledge
    draw_dimension(
        target,
        ledge_2,
        (ledge_2[0], ledge_1[1]),
        location=(ledge_2[0] + 300.0 * s, pcy),
        text_override=_format_dim(cd + 2.0 * ledge, is_metric),
        layer="Dimension",
    )

    # 6. Plan Title
    if title is None:
        title = f"Plan of F{foot_id}"
    draw_text(
        target,
        title,
        position=(pcx, foot_1[1] - 500.0 * s),
        height=txt_sz,
        align="middle_center",
        layer="Text",
    )

    min_x = foot_1[0] - max(cen_ext + 150.0 * s, 300.0 * s)
    max_x = foot_2[0] + max(cen_ext + 150.0 * s, 350.0 * s)
    min_y = foot_1[1] - 500.0 * s - txt_sz * 1.5
    max_y = foot_2[1] + max(cen_ext, 250.0 * s)

    return {
        "plan_origin": (pcx, pcy),
        "bounding_box": (min_x, min_y, max_x, max_y),
    }


__all__ = ["section_view", "plan_view", "bar_off_y"]
