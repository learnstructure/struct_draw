"""struct_draw.elements.footing — Plan + section views for spread footings.

The drawing conventions in this module are inherited from
``references/footing.py`` (the high-quality hand-drawn example):

* Use distinct layers for ``FOUNDATION``, ``COLUMN``, ``REBAR``,
  ``DIM_LINEAR``, ``LEVEL``, ``CEN``, ``TEXT``.
* Mirror the right half of the section view about the vertical
  centerline so only the left half is drawn explicitly.
* Use MLeader-style annotation with the bar call-out
  ``"<n>φ @ <s>mm c/c bothways"``.
* Show the development-length ``Ld`` kink next to the column bar
  hook into the footing.
* Show break-line at the top of long column elevations.
* Mark GL / PL with horizontal lines and text.
* Use closed rectangles for the column-section symbol at the top
  of the section view.

Element functions are completely engineering-agnostic — they only
read :class:`struct_draw.core.data.FootingData` fields.
"""

from __future__ import annotations

from typing import Any, Sequence

from struct_draw.core.composite import (
    draw_break_line,
    draw_concrete_outline,
    draw_dimension,
    draw_leader,
    draw_level_marker,
    draw_line,
    draw_polyline,
    draw_rebar_circle,
    draw_section_cut_symbol,
    draw_text,
)
from struct_draw.core.data import FootingData, Rebar
from struct_draw.core.geometry import mirror_polyline_x
from struct_draw.core.primitives import draw_rectangle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _draw_rebar_layer_x(
    target: Any,
    *,
    x_start: float,
    x_end: float,
    y: float,
    bar_dia: float,
    spacing: float,
) -> list[Any]:
    """Draw a row of rebar cross-section dots between ``x_start`` and ``x_end``.

    The first dot is offset by ``bar_dia`` from ``x_start`` (so it
    doesn't overlap the cover edge). Spacing between dots is
    ``spacing``. Returns the list of drawn entities.
    """
    out: list[Any] = []
    x = x_start + bar_dia
    while x <= x_end - bar_dia:
        out.append(draw_rebar_circle(target, (x, y), diameter=bar_dia * 1.2, layer="REBAR"))
        x += spacing
    return out


def _draw_footing_section_left_half(
    target: Any,
    footing: FootingData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
) -> dict[str, Any]:
    """Draw the left half of the footing cross-section view.

    Returns a dict of references (``origin``, ``column_top``,
    ``ground_level``, etc.) the caller uses to place dimensions
    and labels.
    """
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

    refs: dict[str, Any] = {}

    # ----- Foundation outline: foundation slab from left edge to centerline.
    # Top of foundation (concrete top) is at y = t_mid.
    # Bottom is at y = 0 (foundation bottom).
    # Left edge of foundation is at x = -L/2 (mirrored on the right).
    # Sloped region from x=-L/2 to x=-L/2+75-(-L/2) goes from y=0 to y=t_edge.
    edge_off = 75.0
    inner_off = 150.0
    foundation_pts: list[tuple[float, float]] = [
        (-L / 2.0 + ox, 0.0 + oy),
        (L / 2.0 + ox, 0.0 + oy),  # bottom edge (full width)
        (L / 2.0 + ox, t_edge + oy),  # right edge of sloped region
        (L / 2.0 - edge_off + ox, t_edge + oy),
        (L / 2.0 - inner_off + ox, t_mid + oy),
        (-L / 2.0 + inner_off + ox, t_mid + oy),
        (-L / 2.0 + edge_off + ox, t_edge + oy),
        (-L / 2.0 + ox, t_edge + oy),
        (-L / 2.0 + ox, 0.0 + oy),
    ]
    # Draw full closed polyline.
    draw_polyline(target, foundation_pts, close=True, layer="FOUNDATION")

    # ----- Column outline: from column centerline upward.
    col_x_left = -cw / 2.0 + ox
    col_x_right = cw / 2.0 + ox
    col_y_top = ch + fd + pl + oy  # top of column (ext_top height above GL)
    col_pts = [
        (col_x_left, t_mid + oy),
        (col_x_left + 100.0, t_mid + oy),  # ledge on left
        (col_x_left + 100.0, col_y_top),
        (col_x_right - 100.0, col_y_top),
        (col_x_right - 100.0, t_mid + oy),
        (col_x_right, t_mid + oy),
        (col_x_right, col_y_top),
        (col_x_left, col_y_top),
        (col_x_left, t_mid + oy),
    ]
    draw_polyline(target, col_pts, close=True, layer="COLUMN")

    # ----- Bottom longitudinal rebar (footing bars along length).
    bar_y = t_edge + bar_off_y(footing)
    bar_dia = footing.bar_dia_in
    spacing = footing.bar_spacing_in
    x_left = -L / 2.0 + ox + bar_dia
    x_right = L / 2.0 + ox - bar_dia
    _draw_rebar_layer_x(
        target,
        x_start=x_left,
        x_end=x_right,
        y=bar_y,
        bar_dia=bar_dia,
        spacing=spacing,
    )
    # Mirror to top of footing (top transverse bar).
    top_bar_y = t_mid - bar_off_y(footing)
    _draw_rebar_layer_x(
        target,
        x_start=x_left,
        x_end=x_right,
        y=top_bar_y,
        bar_dia=bar_dia,
        spacing=spacing,
    )

    # ----- Column bars running down into the footing (centerline).
    cb_y_top = col_y_top
    cb_y_bot = bar_y + 0.5
    cb_x = ox
    draw_line(target, (cb_x, cb_y_bot), (cb_x, cb_y_top), layer="REBAR")
    # Off-center column bars.
    for dx in (-cd / 4.0, cd / 4.0):
        draw_line(target, (cb_x + dx, cb_y_bot), (cb_x + dx, cb_y_top), layer="REBAR")

    # ----- Footing bar transverse (across width, drawn as a single horizontal).
    transverse_y = bar_y
    draw_line(target, (x_left, transverse_y), (x_right, transverse_y), layer="REBAR")

    # ----- Column stirrups (one per spacing interval).
    cs = footing.column_stirrups
    stirrup_w = cw - 2.0 * footing.cover_in
    stirrup_h = ch + pl + fd
    spacing_in = cs.spacing_in if cs.spacing_in > 0 else 6.0
    n_stirrups = int(stirrup_h / spacing_in) + 1
    stirrup_y0 = 100.0 + oy
    for i in range(n_stirrups):
        y = stirrup_y0 + i * spacing_in
        if y > col_y_top:
            break
        pts = [
            (col_x_left + footing.cover_in, y),
            (col_x_right - footing.cover_in, y),
        ]
        draw_line(target, pts[0], pts[1], layer="STIRRUP")

    # ----- Column bar development length "Ld" hook (90° bend into the footing).
    Ld = footing.development_length_in
    pcf1_x = -L * 0.35 + ox
    pcf1_y = bar_y + 0.5
    ld_pts = [
        (col_x_right - 50.0, t_mid + oy - 50.0),
        (col_x_right - 20.0, t_mid + oy - 50.0),
        (col_x_right, t_mid + oy),
        (col_x_right + 20.0, t_mid + oy - 50.0),
        (col_x_right - 50.0, t_mid + oy - 50.0),
        (col_x_right - 50.0, t_mid + oy - footing.mid_thickness_in + 130.0),
        (pcf1_x + 50.0, pcf1_y + 45.0),
        (pcf1_x + 50.0, pcf1_y + 25.0),
        (pcf1_x, pcf1_y + 45.0),
        (pcf1_x + 50.0, pcf1_y + 65.0),
        (pcf1_x + 50.0, pcf1_y + 45.0),
    ]
    draw_polyline(target, ld_pts, close=False, layer="DIM_LINEAR")
    draw_text(target, "Ld", position=(col_x_right - 130.0, t_mid - 150.0 + oy),
              height=0.30, layer="TEXT")

    # ----- Break line at top of column elevation (continues above).
    bp_x = -cw / 2.0 - footing.cover_in - 100.0 + ox
    bp_y = col_y_top
    draw_break_line(target, p1=(bp_x, bp_y - 1.0), p2=(bp_x, bp_y + 100.0), layer="BREAK_LINE")

    # ----- Level markers GL / PL.
    gl_y = fd + oy
    pl_y = fd + pl + oy
    draw_level_marker(target, anchor=(col_x_left - 100.0, gl_y), direction="left",
                      length=400.0, label="Ground Lvl.",
                      label_offset=(-300.0, -10.0), text_height=0.25)
    draw_level_marker(target, anchor=(col_x_left - 100.0, pl_y), direction="left",
                      length=400.0, label="Plinth Lvl.",
                      label_offset=(-300.0, -10.0), text_height=0.25)

    refs.update({
        "origin": (ox, oy),
        "column_top": col_y_top,
        "ground_level": gl_y,
        "plinth_level": pl_y,
        "footing_length": L,
        "footing_width": B,
        "mid_thickness": t_mid,
        "edge_thickness": t_edge,
        "column_left_x": col_x_left,
        "column_right_x": col_x_right,
    })
    return refs


def bar_off_y(footing: FootingData) -> float:
    """The vertical offset of a footing bar from the concrete face.

    Equals ``cover + bar_dia / 2``.
    """
    return footing.cover_in + footing.bar_dia_in / 2.0


# ---------------------------------------------------------------------------
# Public view functions
# ---------------------------------------------------------------------------


def section_view(
    target: Any,
    footing: FootingData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
) -> dict[str, Any]:
    """Draw a full cross-section of ``footing`` (with mirrored right half).

    The left half is drawn explicitly; the right half is generated
    by mirroring the bottom-half foundation outline, the column
    outline, the rebar layout, and the level markers about the
    vertical centerline ``x = origin[0]``.

    Returns a metadata dict with the references produced during the
    draw (useful for downstream annotation or testing).
    """
    refs = _draw_footing_section_left_half(target, footing, origin=origin)
    ox, oy = origin
    cw = footing.column_width_in
    cd = footing.column_depth_in

    # Mirror the foundation bottom outline to fill in the right half.
    foundation_pts = [
        (-footing.length_in / 2.0 + ox, 0.0 + oy),
        (footing.length_in / 2.0 + ox, 0.0 + oy),
    ]
    mirrored = mirror_polyline_x(foundation_pts, x_axis=ox)
    draw_polyline(target, mirrored, close=False, layer="FOUNDATION")

    # ----- Dimensions (placed below and to the left of the section).
    L = footing.length_in
    y_below = -1.5 * footing.mid_thickness_in
    draw_dimension(
        target,
        (-L / 2.0 + ox, 0.0 + oy),
        (L / 2.0 + ox, 0.0 + oy),
        location=(ox, y_below),
        text_override=f"{int(L)}\"",
        layer="DIM_LINEAR",
    )
    draw_dimension(
        target,
        (-L / 2.0 + ox, 0.0 + oy),
        (-L / 2.0 + ox, footing.mid_thickness_in + oy),
        location=(-L / 2.0 - 3.0 + ox, footing.mid_thickness_in / 2.0 + oy),
        text_override=f"{int(footing.mid_thickness_in)}\"",
        layer="DIM_LINEAR",
    )

    # ----- Section title and section-cut label.
    if title is None:
        title = f"Section of F{footing.name[1:] if footing.name.startswith('F') else footing.name} at X{footing.name}"
    draw_text(target, title, position=(-L / 2.0 - 8.0 + ox, y_below - 4.0),
              height=0.50, layer="TEXT")

    draw_section_cut_symbol(target, center=(L / 2.0 + 4.0 + ox, footing.mid_thickness_in + oy),
                             letter="X", size=0.6, layer="SECTION_CUT")

    return refs


def plan_view(
    target: Any,
    footing: FootingData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
) -> dict[str, Any]:
    """Draw the plan view of ``footing``.

    The plan shows the footing rectangle, the column rectangle, the
    pedestal ledge rectangle, the footing rebar layout (with both
    layers), and the section-cut symbol that points back to
    :func:`section_view`.

    The rebar call-out is shown via an MLeader-style multi-vertex
    leader with the standard ACI text
    ``"<n>φ @ <s>\" c/c bothways"``.
    """
    ox, oy = origin
    L = footing.length_in
    B = footing.width_in
    cw = footing.column_width_in
    cd = footing.column_depth_in

    # Plan center reference point.
    pcx, pcy = ox, oy

    # Column rectangle (centered on plan center).
    col_corner1 = (pcx - cw / 2.0, pcy - cd / 2.0)
    col_corner2 = (pcx + cw / 2.0, pcy + cd / 2.0)
    draw_rectangle(target, origin=col_corner1, width=cw, height=cd, layer="COLUMN")

    # Pedestal / ledge (column + ledge margin).
    ledge = 100.0
    ledge_corner1 = (pcx - cw / 2.0 - ledge, pcy - cd / 2.0 - ledge)
    ledge_corner2 = (pcx + cw / 2.0 + ledge, pcy + cd / 2.0 + ledge)
    draw_rectangle(target, origin=ledge_corner1,
                   width=(ledge_corner2[0] - ledge_corner1[0]),
                   height=(ledge_corner2[1] - ledge_corner1[1]),
                   layer="FOUNDATION")

    # Footing rectangle.
    foot_corner1 = (pcx - L / 2.0, pcy - B / 2.0)
    foot_corner2 = (pcx + L / 2.0, pcy + B / 2.0)
    draw_rectangle(target, origin=foot_corner1,
                   width=L, height=B, layer="FOUNDATION")

    # Diagonal ledge-to-foot lines (left and right).
    draw_line(target, ledge_corner1, foot_corner1, layer="FOUNDATION")
    draw_line(target, (ledge_corner2[0], ledge_corner1[1]),
              (foot_corner2[0], foot_corner1[1]), layer="FOUNDATION")
    draw_line(target, (ledge_corner1[0], ledge_corner2[1]),
              (foot_corner1[0], foot_corner2[1]), layer="FOUNDATION")
    draw_line(target, ledge_corner2, foot_corner2, layer="FOUNDATION")

    # Plan rebar rows: bottom transverse (along L) and vertical (along B).
    bar_dia = footing.bar_dia_in
    spacing = footing.bar_spacing_in
    cover = footing.cover_in

    # Bottom rebar layer: along x from foot_corner1[0]+cover to foot_corner2[0]-cover.
    # Each bar represented as a series of small dots (cross-section through the bar).
    x_left = foot_corner1[0] + cover
    x_right = foot_corner2[0] - cover
    y_bottom = foot_corner1[1] + cover + bar_dia
    y_top = foot_corner2[1] - cover - bar_dia
    _draw_rebar_layer_x(
        target, x_start=x_left, x_end=x_right, y=y_bottom,
        bar_dia=bar_dia, spacing=spacing,
    )
    _draw_rebar_layer_x(
        target, x_start=x_left, x_end=x_right, y=y_top,
        bar_dia=bar_dia, spacing=spacing,
    )

    # Vertical bars (along B): only at L edges.
    y_step = spacing
    y = y_bottom
    while y <= y_top:
        draw_rebar_circle(target, (x_left, y), diameter=bar_dia * 1.2, layer="REBAR")
        draw_rebar_circle(target, (x_right, y), diameter=bar_dia * 1.2, layer="REBAR")
        y += y_step

    # MLeader-style bar call-out.
    bar_dia_int = int(round(bar_dia * 8.0 / 0.5))  # nominal "#" of bar (rough)
    text_bar = f"{bar_dia_int}φ @ {int(spacing)}\" c/c bothways"
    bar_p1 = (pcx + cw / 2.0, foot_corner1[1] + 70.0)
    bar_p2 = (pcx + cw / 2.0 + 150.0, foot_corner2[1] + 100.0)
    bar_p3 = (pcx + cw / 2.0 + 300.0, foot_corner2[1] + 100.0)
    draw_leader(target, [bar_p1, bar_p2, bar_p3], text=text_bar, layer="LEADER")

    # Dimensions: footing plan length and width.
    dim_offset = 100.0
    draw_dimension(
        target,
        foot_corner1,
        (foot_corner2[0], foot_corner1[1]),
        location=(pcx, foot_corner1[1] - dim_offset),
        text_override=f"{int(L)}\"x{int(B)}\"",
        layer="DIM_LINEAR",
    )
    draw_dimension(
        target,
        foot_corner1,
        (foot_corner1[0], foot_corner2[1]),
        location=(foot_corner1[0] - dim_offset, pcy),
        text_override=f"{int(B)}\"",
        layer="DIM_LINEAR",
    )

    # Plan title.
    if title is None:
        title = f"Plan of F{footing.name[1:] if footing.name.startswith('F') else footing.name}"
    draw_text(target, title, position=(foot_corner1[0] + 50.0, foot_corner2[1] + 200.0),
              height=0.40, layer="TEXT")

    # Section cut label (X1 → X2 leader).
    s_label_pos = (foot_corner2[0] + 200.0, pcy)
    draw_text(target, f"X{footing.name[1:] if footing.name.startswith('F') else footing.name}",
              position=(s_label_pos[0] + 50.0, s_label_pos[1] + 50.0),
              height=0.35, layer="CEN")
    draw_text(target, footing.name,
              position=(ledge_corner2[0] + 50.0, ledge_corner2[1] + 100.0),
              height=0.40, layer="TEXT")

    return {"plan_origin": (pcx, pcy)}


__all__ = ["section_view", "plan_view", "bar_off_y"]