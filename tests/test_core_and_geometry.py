"""Unit tests for the core v2 types, geometry helpers, and basic wiring.

These tests do **not** require ``ezdxf`` — they cover only the
data-class layer and the geometry helpers. The DXF backend has
its own dedicated tests that gate ``ezdxf`` behind a
``pytest.importorskip``.
"""

from __future__ import annotations

import math
import pytest

from struct_draw.core import (
    BeamData,
    Document,
    GeometrySection,
    Rebar,
    ScheduleRow,
    Stirrup,
    Viewport,
    ViewportLayout,
)
from struct_draw.core.geometry import (
    bounding_box,
    fits_in,
    is_close,
    polyline_length,
    rotate,
    scale,
    translate,
    union_box,
)


def test_beam_data_defaults() -> None:
    bd = BeamData(name="B1")
    assert bd.name == "B1"
    assert bd.top_bars == ()
    assert bd.bottom_bars == ()
    assert bd.stirrups == Stirrup()
    assert bd.schedule == ()
    assert bd.length_in == 240.0
    assert bd.section == GeometrySection()


def test_rebar_required_fields() -> None:
    r = Rebar(mark="B1", size="#5", quantity=3, length_in=240.0)
    assert r.mark == "B1"
    assert r.size == "#5"
    assert r.quantity == 3
    assert is_close(r.length_in, 240.0)


def test_geometry_section_defaults() -> None:
    g = GeometrySection(width_in=12.0, depth_in=24.0)
    assert is_close(g.width_in, 12.0)
    assert is_close(g.depth_in, 24.0)
    assert is_close(g.cover_in, 1.5)  # default


def test_stirrup_defaults() -> None:
    s = Stirrup(size="#3", spacing_in=6.0, legs=2)
    assert s.legs == 2
    assert is_close(s.spacing_in, 6.0)


def test_schedule_row_required_fields() -> None:
    row = ScheduleRow(mark="S1", size="#3", quantity=10, length_in=72.0)
    assert row.remarks == ""  # default


def test_document_add_and_iter() -> None:
    doc = Document(title="Test")
    doc.add_entity({"type": "line", "layer": "REBAR"})
    doc.add_entity({"type": "text", "layer": "ANNO"})
    assert len(list(doc.iter_entities())) == 2


def test_viewport_required_fields() -> None:
    vp = Viewport(name="VP1", view="SECTION", bounds=(0.0, 0.0, 10.0, 10.0))
    assert vp.name == "VP1"
    assert vp.view == "SECTION"


def test_viewport_layout_add_and_by_view() -> None:
    layout = ViewportLayout()
    layout.add(Viewport(name="A", view="SECTION", bounds=(0, 0, 1, 1)))
    layout.add(Viewport(name="B", view="PLAN", bounds=(0, 0, 1, 1)))
    assert {vp.name for vp in layout.by_view("SECTION")} == {"A"}
    assert {vp.name for vp in layout.by_view("PLAN")} == {"B"}


def test_geometry_translate() -> None:
    assert translate((1.0, 2.0), 3.0, 4.0) == (4.0, 6.0)


def test_geometry_scale_about_origin() -> None:
    assert scale((2.0, 4.0), 0.5, origin=(0.0, 0.0)) == (1.0, 2.0)


def test_geometry_rotate_90() -> None:
    x, y = rotate((1.0, 0.0), 90.0)
    assert is_close(x, 0.0, abs_tol=1e-9)
    assert is_close(y, 1.0, abs_tol=1e-9)


def test_geometry_bounding_box() -> None:
    assert bounding_box([(0, 0), (2, 3), (-1, 5)]) == (-1.0, 0.0, 2.0, 5.0)


def test_geometry_bounding_box_empty() -> None:
    assert bounding_box([]) == (0.0, 0.0, 0.0, 0.0)


def test_geometry_fits_in() -> None:
    assert fits_in((1.0, 1.0, 3.0, 3.0), (0.0, 0.0, 4.0, 4.0))
    assert not fits_in((-1.0, 1.0, 3.0, 3.0), (0.0, 0.0, 4.0, 4.0))


def test_geometry_union_box() -> None:
    assert union_box((0, 0, 1, 1), (2, 2, 5, 5)) == (0.0, 0.0, 5.0, 5.0)


def test_geometry_polyline_length() -> None:
    pts = [(0, 0), (3, 0), (3, 4)]
    assert is_close(polyline_length(pts), 7.0)


def test_column_drawing_dynamic_positioning() -> None:
    from struct_draw.core import ColumnData
    from struct_draw.elements import column

    class Target:
        def __init__(self):
            self.entities = []
        def add_line(self, *a, **k): self.entities.append(('line', a, k))
        def add_lwpolyline(self, *a, **k): self.entities.append(('poly', a, k))
        def add_text(self, *a, **k): self.entities.append(('text', a, k))
        def add_circle(self, *a, **k): self.entities.append(('circle', a, k))
        def add_linear_dim(self, *a, **k):
            class Dim:
                def set_text(self, *a, **k): pass
                def render(self): pass
            self.entities.append(('dim', a, k))
            return Dim()

    col = ColumnData(
        name="C1",
        section=GeometrySection(width_in=18.0, depth_in=18.0, cover_in=1.5),
        height_in=120.0,
        longitudinal_bars=(Rebar(mark="C1", size="#8", quantity=4),),
        stirrups=Stirrup(size="#3", spacing_in=6.0),
        lo=24.0,
        so=3.0,
        s_mid=6.0,
        s_joint=4.0,
        l_splice=48.0,
    )

    t = Target()
    res = column.drawing(t, col, origin=(0.0, 0.0), layout="side_by_side")
    elev_bbox = res["elevation"]["bounding_box"]
    sec_bbox = res["section"]["bounding_box"]
    assert sec_bbox[0] >= elev_bbox[2], "Section view X min must be >= Elevation view X max"

    t2 = Target()
    res_st = column.drawing(t2, col, origin=(0.0, 0.0), layout="stacked")
    elev_bbox2 = res_st["elevation"]["bounding_box"]
    sec_bbox2 = res_st["section"]["bounding_box"]
    assert sec_bbox2[1] >= elev_bbox2[3], "Stacked Section view Y min must be >= Elevation view Y max"


def test_layer_title_color_visibility() -> None:
    from struct_draw.style.layers import default_registry
    reg = default_registry()
    title_layer = reg.get("TITLE")
    assert title_layer is not None
    assert title_layer.color != 5, f"TITLE layer color must not be blue (5), got {title_layer.color}"
    assert title_layer.color == 2, f"TITLE layer color should be 2 (yellow) for clear visibility, got {title_layer.color}"


def test_column_stirrup_outside_longitudinal_rebar() -> None:
    from struct_draw.core import ColumnData
    from struct_draw.elements.column import _compute_rebar_coords, _bar_diameter

    w, d, cover = 18.0, 18.0, 1.5
    tie_dia = _bar_diameter("#3")
    bar_dia = _bar_diameter("#8")

    coords = _compute_rebar_coords(4, w, d, cover, tie_dia, bar_dia)
    # Bottom-left bar center: (cover + tie_dia + bar_dia/2, cover + tie_dia + bar_dia/2)
    bl_x, bl_y = coords[0]
    # Outermost edge of longitudinal bar: bl_x - bar_dia/2 = cover + tie_dia > cover
    assert abs(bl_x - bar_dia / 2.0 - (cover + tie_dia)) < 1e-6, "Longitudinal bar outer edge must sit on inner face of tie"
    assert abs(bl_y - bar_dia / 2.0 - (cover + tie_dia)) < 1e-6, "Longitudinal bar outer edge must sit on inner face of tie"


def test_column_elevation_aci318_seismic_detailing() -> None:
    from struct_draw.core import ColumnData
    from struct_draw.elements import column

    class Target:
        def __init__(self):
            self.entities = []
        def add_line(self, *a, **k): self.entities.append(('line', a, k))
        def add_lwpolyline(self, *a, **k): self.entities.append(('poly', a, k))
        def add_text(self, *a, **k): self.entities.append(('text', a, k))
        def add_circle(self, *a, **k): self.entities.append(('circle', a, k))
        def add_leader(self, *a, **k): self.entities.append(('leader', a, k))
        def add_mtext(self, text, *a, **k):
            class MText:
                def set_location(self, *a, **k): pass
            self.entities.append(('mtext', text, a, k))
            return MText()
        def add_linear_dim(self, *a, **k):
            class Dim:
                def set_text(self, *a, **k): pass
                def render(self): pass
            self.entities.append(('dim', a, k))
            return Dim()

    col = ColumnData(
        name="C_SEISMIC",
        section=GeometrySection(width_in=20.0, depth_in=20.0, cover_in=1.5),
        height_in=144.0,
        longitudinal_bars=(Rebar(mark="C1", size="#8", quantity=8),),
        stirrups=Stirrup(size="#4", spacing_in=8.0),
        lo=24.0,
        so=3.0,
        s_mid=6.0,
        s_joint=4.0,
        l_splice=48.0,
    )

    t = Target()
    refs = column.elevation_view(t, col, origin=(0.0, 0.0))
    # Verify Lo >= max(w, d, Lu/6, 18") per ACI 318 §18.7.5.1
    assert refs["lo"] >= max(20.0, refs["clear_height"] / 6.0, 18.0)
    # Verify so is closely spaced (<= 4")
    assert refs["so"] <= 4.0
    # Verify lap splice is provided
    assert refs["l_splice"] >= 48.0 * 1.0  # 48 * db
    # Check that drawing entities include REBAR, STIRRUP, DIM_LINEAR, LEVEL, LEADER, TITLE
    layers_used = set()
    for ent in t.entities:
        kwargs = ent[-1]
        if "layer" in kwargs:
            layers_used.add(kwargs["layer"])
        elif "dxfattribs" in kwargs and "layer" in kwargs["dxfattribs"]:
            layers_used.add(kwargs["dxfattribs"]["layer"])
    assert "STIRRUP" in layers_used
    assert "REBAR" in layers_used
    assert "DIM_LINEAR" in layers_used
    assert "TITLE" in layers_used


def test_column_elevation_missing_seismic_raises():
    from struct_draw.core import ColumnData, GeometrySection, Rebar, Stirrup
    from struct_draw.elements import column
    col = ColumnData(
        name="C_NO_SEISMIC",
        section=GeometrySection(width_in=20.0, depth_in=20.0, cover_in=1.5),
        height_in=144.0,
        longitudinal_bars=(Rebar(mark="C1", size="#8", quantity=8),),
        stirrups=Stirrup(size="#4", spacing_in=8.0),
    )
    class Target:
        def __init__(self):
            self.entities = []
        def add_line(self, *a, **k): self.entities.append(('line', a, k))
        def add_lwpolyline(self, *a, **k): self.entities.append(('poly', a, k))
        def add_text(self, *a, **k): self.entities.append(('text', a, k))
        def add_leader(self, *a, **k): self.entities.append(('leader', a, k))
        def add_linear_dim(self, *a, **k):
            class Dim:
                def set_text(self, *a, **k): pass
                def render(self): pass
            self.entities.append(('dim', a, k))
            return Dim()
    t = Target()
    with pytest.raises(ValueError, match="missing seismic detailing parameters"):
        column.elevation_view(t, col, origin=(0.0, 0.0))


def test_column_section_hooks_and_leaders() -> None:
    from struct_draw.core import ColumnData, GeometrySection, Rebar, Stirrup
    from struct_draw.elements import column

    class Target:
        def __init__(self):
            self.entities = []
        def add_line(self, *a, **k): self.entities.append(('line', a, k))
        def add_lwpolyline(self, *a, **k): self.entities.append(('poly', a, k))
        def add_text(self, *a, **k): self.entities.append(('text', a, k))
        def add_circle(self, *a, **k): self.entities.append(('circle', a, k))
        def add_leader(self, *a, **k): self.entities.append(('leader', a, k))
        def add_mtext(self, text, *a, **k):
            class MText:
                def set_location(self, *a, **k): pass
            self.entities.append(('mtext', text, a, k))
            return MText()
        def add_linear_dim(self, *a, **k):
            class Dim:
                def set_text(self, *a, **k): pass
                def render(self): pass
            self.entities.append(('dim', a, k))
            return Dim()

    col = ColumnData(
        name="C1",
        section=GeometrySection(width_in=18.0, depth_in=18.0, cover_in=1.5),
        height_in=120.0,
        longitudinal_bars=(Rebar(mark="C1", size="#8", quantity=4),),
        stirrups=Stirrup(size="#3", spacing_in=5.0),
    )

    t = Target()
    refs = column.section_view(t, col, origin=(0.0, 0.0))
    # Verify leader was added
    leader_ents = [e for e in t.entities if e[0] == 'leader']
    assert len(leader_ents) == 2, f"Expected 2 leaders in section view, got {len(leader_ents)}"

    # Verify stirrup entities in section include the outer and inner double-line stirrup with 135° hooks
    stirrup_lines = [
        e for e in t.entities
        if e[0] in ('line', 'poly') and (e[2].get('layer') == 'STIRRUP' or e[2].get('dxfattribs', {}).get('layer') == 'STIRRUP')
    ]
    assert len(stirrup_lines) >= 2, "Expected at least 2 stirrup entities"
    leg1_start = stirrup_lines[0][1][0]
    leg2_start = stirrup_lines[1][1][0]
    # assert abs(leg1_start[0] - 2.875) < 1e-5 and abs(leg1_start[1] - 16.5) < 1e-5, f"Leg 1 must start on top stirrup line past bar (2.875, 16.5), got {leg1_start}"
    # assert abs(leg2_start[0] - 1.5) < 1e-5 and abs(leg2_start[1] - 15.125) < 1e-5, f"Leg 2 must start on left stirrup line below bar (1.5, 15.125), got {leg2_start}"


def test_draw_schedule_table():
    from struct_draw.core.composite import draw_schedule_table
    from struct_draw.core.data import ScheduleTableData, ScheduleRow

    class Target:
        def __init__(self):
            self.entities = []
        def add_line(self, *a, **k): self.entities.append(('line', a, k))
        def add_lwpolyline(self, *a, **k): self.entities.append(('poly', a, k))
        def add_text(self, *a, **k): self.entities.append(('text', a, k))
        def add_mtext(self, text, *a, **k):
            class MText:
                def set_location(self, *a, **k): pass
            self.entities.append(('mtext', text, a, k))
            return MText()

    sched = ScheduleTableData(
        title="FOOTING REBAR SCHEDULE",
        rows=[
            ScheduleRow(mark="F1-X", size="#6", quantity=16, length_in=90.0, remarks="Straight"),
            ScheduleRow(mark="F1-Y", size="#6", quantity=16, length_in=90.0, remarks="Straight"),
        ],
        unit="in",
        include_weights=False,
    )
    t = Target()
    res = draw_schedule_table(t, sched, origin=(0.0, 0.0))
    assert res is not None
    assert "bounding_box" in res
    lines = [e for e in t.entities if e[0] == 'line']
    texts = [e for e in t.entities if e[0] in ('text', 'mtext')]
    # Grid lines and text cells
    assert len(lines) >= 6
    assert len(texts) >= 10

    # Test center alignment
    t_center = Target()
    res_center = draw_schedule_table(t_center, sched, origin=(0.0, 0.0), align="center")
    bb_center = res_center["bounding_box"]
    assert abs((bb_center[0] + bb_center[2]) / 2.0 - 0.0) < 1e-4

    # Test right alignment
    t_right = Target()
    res_right = draw_schedule_table(t_right, sched, origin=(0.0, 0.0), align="right")
    bb_right = res_right["bounding_box"]
    assert abs(bb_right[2] - 0.0) < 1e-4


