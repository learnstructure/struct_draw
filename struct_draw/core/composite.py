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

from struct_draw.core.data import Rebar, ScheduleRow, ScheduleTableData, Stirrup
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
    corner_bar_diameter: float | None = None,
    bend_radius: float | None = None,
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
        corner_bar_diameter=corner_bar_diameter,
        bend_radius=bend_radius,
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
            corner_bar_diameter=corner_bar_diameter,
            bend_radius=bend_radius,
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
    cover: float | None = None,
    tie_diameter: float | None = None,
    bar_diameter: float | None = None,
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
    st_off = cover if (cover is not None and cover > 0) else (25.0 if is_metric else 1.0)
    sw = max(1.0, width - 2.0 * st_off)
    sh = max(1.0, height - 2.0 * st_off)
    sx0 = center_x - width / 2.0 + st_off
    sy0 = top_y - height + st_off
    hook_len = 75.0 if is_metric else 3.0
    tie_dia = tie_diameter if (tie_diameter is not None and tie_diameter > 0) else (10.0 if is_metric else 0.375)
    b_dia = bar_diameter if (bar_diameter is not None and bar_diameter > 0) else (12.0 if is_metric else 0.5)

    st_ents = draw_stirrup_hooked(
        target,
        width=sw,
        height=sh,
        origin=(sx0, sy0),
        hook_length=hook_len,
        corner="top_left",
        tie_diameter=tie_dia,
        corner_bar_diameter=b_dia,
        double_line=True,
        layer=layer_stirrup,
    )
    if st_ents:
        out.extend(st_ents)

    # 3. Longitudinal rebar dots
    # Must be placed inside the inner line of the double-line stirrup.
    # The inner face of the stirrup is at offset `st_off + tie_dia` from concrete face.
    # Longitudinal rebar center: inset = st_off + tie_dia + b_dot so it sits snugly inside.
    b_dia = bar_diameter if (bar_diameter is not None and bar_diameter > 0) else (12.0 if is_metric else 0.5)
    b_dot = b_dia / 2.0
    inset = st_off + tie_dia + b_dot

    x_left = center_x - width / 2.0 + inset
    x_right = center_x + width / 2.0 - inset
    if x_right > x_left + 2.0 * b_dot:
        x_coords = (x_left, center_x, x_right)
    else:
        x_coords = (x_left, x_right)

    y_top = top_y - inset
    y_bot = top_y - height + inset
    y_coords = (y_top, y_bot)

    for cx in x_coords:
        for cy in y_coords:
            c_ent = draw_rebar_circle(target, (cx, cy), diameter=b_dia, layer=layer_rebar)
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



# ---------------------------------------------------------------------------
# Bar Bending Schedule (BBS) Table
# ---------------------------------------------------------------------------

_IMPERIAL_BAR_WEIGHTS: dict[str, float] = {
    "#3": 0.376,
    "#4": 0.668,
    "#5": 1.043,
    "#6": 1.502,
    "#7": 2.044,
    "#8": 2.670,
    "#9": 3.400,
    "#10": 4.303,
    "#11": 5.313,
    "#14": 7.650,
    "#18": 13.60,
}


def _clean_cad_str(text: str) -> str:
    """Sanitize unicode characters for standard CAD text."""
    if not text:
        return ""
    return (
        text.replace("φ", "mm dia")
        .replace("Φ", "mm dia")
        .replace("ϕ", "mm dia")
        .replace("’", "'")
        .replace("‘", "'")
        .replace("”", '"')
        .replace("“", '"')
        .replace("–", "-")
        .replace("—", "-")
    )


def _format_cad_length(length_val: float, is_metric: bool) -> str:
    """Format length into professional engineering callout."""
    if is_metric:
        return f"{int(round(length_val))}" if abs(length_val - round(length_val)) < 0.05 else f"{length_val:.1f}"
    # Imperial: convert inches to feet-inches
    tot_in = round(length_val)
    feet = int(tot_in // 12)
    inches = int(tot_in % 12)
    return f"{feet}'-{inches}\""


def _get_bar_unit_weight(size_str: str, is_metric: bool) -> float:
    """Compute nominal linear weight (lbs/ft for imperial, kg/m for metric)."""
    import re
    s = size_str.strip()
    if not is_metric:
        for k, wt in _IMPERIAL_BAR_WEIGHTS.items():
            if k in s:
                return wt
        m = re.search(r"#?(\d+)", s)
        if m:
            bar_num = int(m.group(1))
            return round(0.04167 * (bar_num ** 2), 2)
        return 0.0
    else:
        m = re.search(r"(\d+(\.\d+)?)", s)
        if m:
            dia_mm = float(m.group(1))
            return round((dia_mm ** 2) / 162.2, 3)
        return 0.0


def draw_schedule_table(
    target: Any,
    table_data: ScheduleTableData | Sequence[ScheduleRow],
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
    scale: Any = None,
    unit: Any = None,
    layer_grid: str = "SCHEDULE",
    layer_text: str = "SCHEDULE",
    text_style_header: str = "Schedule",
    text_style_body: str = "Schedule",
    text_style_title: str = "Title",
    show_weights: bool = True,
    notes: str | None = None,
    align: str = "left",
) -> dict[str, Any]:
    """Draw a production-grade Bar Bending Schedule (BBS) table in CAD modelspace.

    Features:
    * Standard multi-tier header layout:
      MARK | BAR SIZE | QTY (NO.) | LENGTH (ft-in or mm) | SHAPE (TYPE) | UNIT WT | TOTAL WT | REMARKS
    * Automatic unit weight lookup / computation for ASTM A615 (Imperial) and IS 1786 / EN 10080 (Metric).
    * Summary row with grand total estimated reinforcement weight.
    * General rebar material & lap splice engineering notes below table.
    * Professional typography utilizing standard AutoCAD Romans / ISOCP single-line vector fonts.
    * Dynamic column width scaling with generous clearances to prevent text overlaps.
    """
    from struct_draw.core.units import DrawingScale, DrawingUnit, SCALE_1_25, SCALE_1_IN
    from struct_draw.style.annotation_config import DEFAULT_ANNOTATION_CONFIG

    if isinstance(table_data, ScheduleTableData):
        tbl_title = title or table_data.title or "REBAR SCHEDULE"
        rows = list(table_data.rows)
        u_val = unit or table_data.unit
        s_val = scale or table_data.scale
        rem_notes = notes or table_data.remarks
        is_metric = table_data.is_metric
    else:
        tbl_title = title or "REBAR SCHEDULE"
        rows = list(table_data)
        u_val = unit
        s_val = scale
        rem_notes = notes or ""
        if u_val is not None:
            du = DrawingUnit.from_str(u_val)
            is_metric = du.is_metric
        else:
            is_metric = any(r.length_in >= 500.0 for r in rows) if rows else False

    # Annotation heights
    du_enum = DrawingUnit.MM if is_metric else DrawingUnit.IN
    try:
        ds = DrawingScale.from_any(s_val, is_metric=is_metric) if s_val is not None else (SCALE_1_25 if is_metric else SCALE_1_IN)
    except Exception:
        ds = SCALE_1_25 if is_metric else SCALE_1_IN

    body_h = DEFAULT_ANNOTATION_CONFIG.text_height(ds, du_enum)
    title_h = DEFAULT_ANNOTATION_CONFIG.title_height(ds, du_enum)
    hdr_h = body_h * 1.05

    # Headers definition: (Main Header, Sub Header)
    len_unit_label = "mm" if is_metric else "ft-in"
    wt_unit_label = "kg/m" if is_metric else "lbs/ft"
    tot_unit_label = "kg" if is_metric else "lbs"

    header_defs = [
        ("MARK", ""),
        ("BAR SIZE", ""),
        ("QTY", "NO."),
        ("LENGTH", len_unit_label),
        ("SHAPE", "TYPE"),
    ]
    if show_weights:
        header_defs.extend([
            ("UNIT WT", wt_unit_label),
            ("TOTAL WT", tot_unit_label),
        ])
    header_defs.append(("REMARKS", ""))

    # Prepare data rows
    data_rows: list[list[str]] = []
    grand_total_wt = 0.0

    for r in rows:
        m_str = _clean_cad_str(r.mark)
        s_str = _clean_cad_str(r.size)
        q_str = str(r.quantity)
        l_str = _format_cad_length(r.length_in, is_metric)
        shape_val = getattr(r, "shape_code", None) or getattr(r, "shape_type", None) or getattr(r, "shape", None)
        sh_str = _clean_cad_str(shape_val) if shape_val else (
            "Stirrup" if ("T" in m_str or "X" in m_str or "tie" in r.remarks.lower() or "stirrup" in r.remarks.lower() or "hoop" in r.remarks.lower()) else "Straight"
        )
        row_vals = [m_str, s_str, q_str, l_str, sh_str]

        if show_weights:
            custom_uwt = getattr(r, "unit_weight", None) or getattr(r, "unit_weight_lbs_per_ft", None)
            unit_wt = float(custom_uwt) if (custom_uwt is not None and custom_uwt > 0) else _get_bar_unit_weight(r.size, is_metric)
            custom_twt = getattr(r, "total_weight", None)
            if custom_twt is not None and custom_twt > 0:
                total_wt = float(custom_twt)
            elif is_metric:
                total_wt = r.quantity * (r.length_in / 1000.0) * unit_wt
            else:
                total_wt = r.quantity * (r.length_in / 12.0) * unit_wt
            grand_total_wt += total_wt

            uwt_str = f"{unit_wt:.3f}" if (is_metric and unit_wt < 1.0) else f"{unit_wt:.2f}"
            twt_str = f"{total_wt:.1f}"
            row_vals.extend([uwt_str, twt_str])

        rem_str = _clean_cad_str(r.remarks)
        row_vals.append(rem_str)
        data_rows.append(row_vals)

    # Dynamic column widths
    col_widths: list[float] = []
    for col_idx, (h_main, h_sub) in enumerate(header_defs):
        max_chars = max(len(h_main), len(h_sub))
        for row in data_rows:
            max_chars = max(max_chars, len(row[col_idx]))
        calc_w = (max_chars * 0.95 + 3.5) * body_h
        min_w = 6.0 * body_h
        col_widths.append(max(calc_w, min_w))

    table_w = sum(col_widths)
    title_min_w = (len(_clean_cad_str(tbl_title)) * 0.95 + 4.0) * title_h
    if table_w < title_min_w:
        col_widths[-1] += (title_min_w - table_w)
        table_w = sum(col_widths)

    title_row_h = title_h * 2.4
    hdr_row_h = hdr_h * 2.8
    data_row_h = body_h * 2.0
    total_row_h = data_row_h if show_weights else 0.0

    ox, oy = origin
    if align == "center":
        ox = ox - table_w / 2.0
    elif align == "right":
        ox = ox - table_w

    entities: list[Any] = []

    # 1. Title Row
    entities.append(draw_rectangle(target, origin=(ox, oy - title_row_h), width=table_w, height=title_row_h, layer=layer_grid))
    entities.append(
        draw_text(
            target,
            _clean_cad_str(tbl_title),
            position=(ox + table_w / 2.0, oy - title_row_h / 2.0),
            height=title_h,
            style=text_style_title,
            align="MIDDLE_CENTER",
            layer=layer_text,
        )
    )

    # 2. Header Row
    hdr_top_y = oy - title_row_h
    hdr_bot_y = hdr_top_y - hdr_row_h
    entities.append(draw_rectangle(target, origin=(ox, hdr_bot_y), width=table_w, height=hdr_row_h, layer=layer_grid))

    curr_x = ox
    for idx, ((h_main, h_sub), cw) in enumerate(zip(header_defs, col_widths)):
        if idx > 0:
            entities.append(draw_line(target, (curr_x, hdr_top_y), (curr_x, hdr_bot_y), layer=layer_grid))
        col_cx = curr_x + cw / 2.0
        if h_sub:
            entities.append(draw_text(target, h_main, position=(col_cx, hdr_top_y - hdr_row_h * 0.35), height=hdr_h, style=text_style_header, align="MIDDLE_CENTER", layer=layer_text))
            entities.append(draw_text(target, h_sub, position=(col_cx, hdr_top_y - hdr_row_h * 0.72), height=hdr_h * 0.82, style=text_style_header, align="MIDDLE_CENTER", layer=layer_text))
        else:
            entities.append(draw_text(target, h_main, position=(col_cx, hdr_top_y - hdr_row_h * 0.5), height=hdr_h, style=text_style_header, align="MIDDLE_CENTER", layer=layer_text))
        curr_x += cw

    # 3. Data Rows
    curr_top_y = hdr_bot_y
    for row_vals in data_rows:
        row_bot_y = curr_top_y - data_row_h
        entities.append(draw_rectangle(target, origin=(ox, row_bot_y), width=table_w, height=data_row_h, layer=layer_grid))

        c_left = ox
        for col_idx, (val, cw) in enumerate(zip(row_vals, col_widths)):
            if col_idx > 0:
                entities.append(draw_line(target, (c_left, curr_top_y), (c_left, row_bot_y), layer=layer_grid))
            mid_y = curr_top_y - data_row_h / 2.0
            is_remarks = (col_idx == len(row_vals) - 1)
            if is_remarks:
                cx = c_left + body_h * 1.0
                entities.append(draw_text(target, val, position=(cx, mid_y), height=body_h, style=text_style_body, align="MIDDLE_LEFT", layer=layer_text))
            else:
                cx = c_left + cw / 2.0
                entities.append(draw_text(target, val, position=(cx, mid_y), height=body_h, style=text_style_body, align="MIDDLE_CENTER", layer=layer_text))
            c_left += cw
        curr_top_y = row_bot_y

    # 4. Total Summary Row
    if show_weights:
        tot_bot_y = curr_top_y - total_row_h
        entities.append(draw_rectangle(target, origin=(ox, tot_bot_y), width=table_w, height=total_row_h, layer=layer_grid))

        # Col 0..4 divider at col 5
        col5_x = ox + sum(col_widths[:5])
        col6_x = col5_x + col_widths[5]
        col7_x = col6_x + col_widths[6]

        entities.append(draw_line(target, (col6_x, curr_top_y), (col6_x, tot_bot_y), layer=layer_grid))
        entities.append(draw_line(target, (col7_x, curr_top_y), (col7_x, tot_bot_y), layer=layer_grid))

        lbl_cx = ox + sum(col_widths[:6]) / 2.0
        entities.append(draw_text(target, "TOTAL ESTIMATED WEIGHT", position=(lbl_cx, curr_top_y - total_row_h / 2.0), height=body_h * 1.05, style=text_style_header, align="MIDDLE_CENTER", layer=layer_text))

        twt_val_str = f"{grand_total_wt:.1f} {tot_unit_label}"
        val_cx = col6_x + col_widths[6] / 2.0
        entities.append(draw_text(target, twt_val_str, position=(val_cx, curr_top_y - total_row_h / 2.0), height=body_h * 1.05, style=text_style_header, align="MIDDLE_CENTER", layer=layer_text))

        curr_top_y = tot_bot_y

    # 5. Notes below table
    notes_h = 0.0
    if rem_notes:
        note_y = curr_top_y - body_h * 1.2
        entities.append(
            draw_text(
                target,
                f"NOTE: {_clean_cad_str(rem_notes)}",
                position=(ox, note_y),
                height=body_h * 0.88,
                style=text_style_body,
                align="TOP_LEFT",
                layer=layer_text,
            )
        )
        notes_h = body_h * 2.5

    total_h = (oy - curr_top_y) + notes_h
    bbox = (ox, curr_top_y - notes_h, ox + table_w, oy)

    return {
        "bounding_box": bbox,
        "width": table_w,
        "height": total_h,
        "total_weight": grand_total_wt,
        "entities": entities,
    }


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
    "draw_schedule_table",
]