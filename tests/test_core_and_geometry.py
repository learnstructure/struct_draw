"""Unit tests for the core v2 types, geometry helpers, and basic wiring.

These tests do **not** require ``ezdxf`` — they cover only the
data-class layer and the geometry helpers. The DXF backend has
its own dedicated tests that gate ``ezdxf`` behind a
``pytest.importorskip``.
"""

from __future__ import annotations

import math

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
    assert bd.stirrups is None
    assert bd.schedule == ()
    assert bd.length_in == 0.0
    assert bd.section is None


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