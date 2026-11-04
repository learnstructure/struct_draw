"""
Unit tests for struct_draw.adapters.struct_core_adapter.
"""

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
import ezdxf
import pytest

try:
    from struct_core import (
        Bar,
        BarLayout,
        BarSchedule,
        BarScheduleItem,
        DetailingResult,
        ElementDetailingResult,
        RebarLayer,
        StirrupLayout,
    )
except ImportError:
    @dataclass
    class Bar:
        mark: str = "1B1"
        size: int = 8
        count: int = 3
        length: float = 240.0
        weight: float = 64.0

    @dataclass
    class RebarLayer:
        depth: float = 15.5
        bars: List[Bar] = field(default_factory=list)

    @dataclass
    class StirrupLayout:
        size: int = 3
        spacing: float = 6.0
        legs: int = 2
        start_zone: float = 0.0
        end_zone: float = 240.0

    @dataclass
    class BarLayout:
        bottom_layers: List[RebarLayer] = field(default_factory=list)
        top_layers: List[RebarLayer] = field(default_factory=list)
        stirrups: List[StirrupLayout] = field(default_factory=list)

    @dataclass
    class BarScheduleItem:
        mark: str = "1B1"
        bar_size: int = 8
        quantity: int = 3
        cut_length: float = 240.0
        total_length: float = 720.0
        weight: float = 64.0
        shape_code: str = "STRAIGHT"
        location: str = "Beam B1"

    @dataclass
    class BarSchedule:
        items: List[BarScheduleItem] = field(default_factory=list)
        total_weight: float = 64.0

    @dataclass
    class ElementDetailingResult:
        element_id: int = 1
        member_type: str = "beam"
        bar_layout: Optional[BarLayout] = None
        bar_schedule: Optional[BarSchedule] = None

    @dataclass
    class DetailingResult:
        element_results: Dict[Any, ElementDetailingResult] = field(default_factory=dict)

from struct_draw.adapters import draw_from_core


def test_draw_from_core_beam():
    # 1. Create a struct_core ElementDetailingResult for a beam
    main_bar = Bar(mark="1B1", size=8, count=3, length=240.0, weight=64.0)
    layer = RebarLayer(depth=15.5, bars=[main_bar])
    stirrup = StirrupLayout(size=3, spacing=6.0, legs=2, start_zone=0.0, end_zone=240.0)
    layout = BarLayout(bottom_layers=[layer], stirrups=[stirrup])

    sched_item = BarScheduleItem(
        mark="1B1",
        bar_size=8,
        quantity=3,
        cut_length=240.0,
        total_length=720.0,
        weight=64.0,
        shape_code="STRAIGHT",
        location="Beam B1",
    )
    schedule = BarSchedule(items=[sched_item], total_weight=64.0)

    elem_detailing = ElementDetailingResult(
        element_id=1,
        member_type="beam",
        bar_layout=layout,
        bar_schedule=schedule,
    )

    detailing_result = DetailingResult(element_results={1: elem_detailing})

    # Pass dynamic geometry via design_result
    beam_design = SimpleNamespace(
        width=14.0,
        depth=26.0,
        cover=2.0,
    )
    design_result = SimpleNamespace(element_results={1: beam_design})

    # 2. Render DXF
    res = draw_from_core(detailing_result, design_result=design_result)

    assert "drawing" in res
    assert hasattr(res["drawing"], "modelspace")
    assert res["elements_drawn"] == 1
    assert 1 in res["data"]
    beam_data = res["data"][1]
    assert beam_data.section.width_in == 14.0
    assert beam_data.section.depth_in == 26.0
    assert beam_data.section.cover_in == 2.0

    # Verify DXF entities in modelspace
    msp = res["drawing"].modelspace()
    assert len(list(msp)) > 0


def test_draw_from_core_all_seven_member_types():
    """Test that struct_core_adapter dispatches all seven member types."""
    # 1. Beam
    e_beam = ElementDetailingResult(element_id=101, member_type="beam")
    d_beam = SimpleNamespace(width=12.0, depth=20.0, cover=1.5)

    # 2. Beam Profile (Continuous Beam)
    e_prof = ElementDetailingResult(element_id=102, member_type="beam_profile")
    d_prof = SimpleNamespace(width=14.0, depth=24.0, spans=[240.0, 300.0], cover=1.5)

    # 3. Column
    e_col = ElementDetailingResult(element_id=103, member_type="column")
    d_col = SimpleNamespace(width=18.0, depth=18.0, cover=1.5)

    # 4. Footing
    e_ftg = ElementDetailingResult(element_id=104, member_type="footing")
    d_ftg = SimpleNamespace(length_in=96.0, width_in=96.0, thickness_in=20.0)

    # 5. Combined Footing
    e_cftg = ElementDetailingResult(element_id=105, member_type="combined_footing")
    d_cftg = SimpleNamespace(col_spacing_in=144.0, width_in=72.0, thickness_in=28.0)

    # 6. Staircase
    e_stair = ElementDetailingResult(element_id=106, member_type="staircase")
    d_stair = SimpleNamespace(flight_width_in=54.0, riser_height_in=6.5)

    # 7. Slab
    e_slab = ElementDetailingResult(element_id=107, member_type="slab")
    d_slab = SimpleNamespace(length_in=260.0, width_in=200.0, thickness_in=7.0)

    all_detailing = {
        101: e_beam,
        102: e_prof,
        103: e_col,
        104: e_ftg,
        105: e_cftg,
        106: e_stair,
        107: e_slab,
    }

    all_design = {
        101: d_beam,
        102: d_prof,
        103: d_col,
        104: d_ftg,
        105: d_cftg,
        106: d_stair,
        107: d_slab,
    }

    detailing_result = DetailingResult(element_results=all_detailing)
    design_result = SimpleNamespace(element_results=all_design)
    res = draw_from_core(detailing_result, design_result=design_result)

    assert res["elements_drawn"] == 7
    assert len(res["data"]) == 7
    assert res["data"][101].section.width_in == 12.0
    assert res["data"][102].beam_depth_in == 24.0
    assert res["data"][103].section.width_in == 18.0
    assert res["data"][104].length_in == 96.0
    assert res["data"][105].col_spacing_in == 144.0
    assert res["data"][106].flight_width_in == 54.0
    assert res["data"][107].thickness_in == 7.0

    msp = res["drawing"].modelspace()
    assert len(list(msp)) > 50


def test_dynamic_geometry_from_model_and_design():
    """Verify geometry extracted from design_result or structural model when detailing lacks it."""
    e_beam = ElementDetailingResult(element_id=1, member_type="beam")

    # Design result mock
    @dataclass
    class ElemDesign:
        width: float = 15.0
        depth: float = 30.0
        cover: float = 2.5

    @dataclass
    class DesignRes:
        element_results: Dict[Any, Any] = field(default_factory=dict)

    des_res = DesignRes(element_results={1: ElemDesign(width=15.0, depth=30.0, cover=2.5)})
    det_res = DetailingResult(element_results={1: e_beam})

    res = draw_from_core(det_res, design_result=des_res)
    beam_data = res["data"][1]
    assert beam_data.section.width_in == 15.0
    assert beam_data.section.depth_in == 30.0
    assert beam_data.section.cover_in == 2.5


def test_2d_model_framing_plan_single_grid_y():
    """Verify that a 2D planar frame produces only a single Y-grid line (no empty Grid 2-2)."""
    from struct_draw.adapters.struct_core_adapter import create_general_frame_data_from_model

    class MockNode:
        def __init__(self, id, x, y, z=0.0):
            self.id = id
            self.x = x
            self.y = y
            self.z = z

    class MockElement:
        def __init__(self, id, start_node, end_node, member_type="beam", name=None):
            self.id = id
            self.start_node = start_node
            self.end_node = end_node
            self.member_type = member_type
            self.name = name

    class MockModel:
        def __init__(self):
            self.nodes = [
                MockNode(1, 0.0, 0.0),
                MockNode(2, 0.0, 3.6),
                MockNode(3, 6.0, 3.6),
                MockNode(4, 6.0, 0.0),
            ]
            self.elements = [
                MockElement(1, 1, 2, "column", "C1"),
                MockElement(2, 2, 3, "beam", "B1"),
                MockElement(3, 4, 3, "column", "C2"),
            ]
            self.story_elevations = [3.6]
            self.sections = []

    model = MockModel()
    frame_data = create_general_frame_data_from_model(model, view_mode="plan")

    assert len(frame_data.grid_y) == 1
    assert frame_data.grid_y[0].label == "1"
    assert frame_data.grid_y[0].coord == 0.0
    assert len(frame_data.grid_x) == 2
    assert [g.label for g in frame_data.grid_x] == ["A", "B"]


def test_2d_multi_story_column_schedule_and_beam_runs():
    """Verify that a 2-bay, 3-story 2D frame has multi-story column schedule and beam L-profile runs."""
    from struct_draw.adapters.struct_core_adapter import _extract_continuous_beam_runs, draw_from_core

    class MockNode:
        def __init__(self, id, x, y, z=0.0):
            self.id = id
            self.x = x
            self.y = y
            self.z = z

    class MockElement:
        def __init__(self, id, start_node, end_node, member_type="beam", name=None):
            self.id = id
            self.start_node = start_node
            self.end_node = end_node
            self.member_type = member_type
            self.name = name

    # 2 bays (6m each, total 12m), 3 stories (3.5m each, total 10.5m)
    nodes = []
    x_coords = [0.0, 6.0, 12.0]
    y_coords = [0.0, 3.5, 7.0, 10.5]
    node_map = {}
    nid = 1
    for j, y in enumerate(y_coords):
        for i, x in enumerate(x_coords):
            nodes.append(MockNode(nid, x, y))
            node_map[(i, j)] = nid
            nid += 1

    elements = []
    # Columns (3 per story, 9 total)
    for j in range(3):
        for i in range(3):
            cid = f"C_{i+1}_{j+1}"
            elements.append(MockElement(cid, node_map[(i, j)], node_map[(i, j+1)], "column", f"C{i+1}"))

    # Beams (2 per story, 6 total)
    for j in range(1, 4):
        for i in range(2):
            bid = f"B_{i+1}_{j}"
            elements.append(MockElement(bid, node_map[(i, j)], node_map[(i+1, j)], "beam", f"B{i+1}"))

    class MockModel:
        def __init__(self):
            self.nodes = nodes
            self.elements = elements
            self.story_elevations = [3.5, 7.0, 10.5]
            self.sections = []
            self.units = "kN, m"

    model = MockModel()

    # 1. Continuous Beam Runs
    elem_results = {e.id: ElementDetailingResult(element_id=e.id, member_type=e.member_type) for e in elements}
    des_results = {e.id: SimpleNamespace(width=14.0, depth=22.0, cover=1.5) for e in elements}
    runs = _extract_continuous_beam_runs(model, elem_results, des_results)

    assert len(runs) == 3
    for run in runs:
        assert len(run.spans_in) == 2
        assert "L-SECTION OF BEAM" in run.name
        assert "LEVEL Y =" in run.level_text

    # 2. Column Schedule Drawing
    det_res = DetailingResult(element_results=elem_results)
    des_res = SimpleNamespace(element_results=des_results)
    res = draw_from_core(det_res, design_result=des_res, model_or_project=model)

    assert "column_schedule" in res["data"]
    sched = res["data"]["column_schedule"]
    assert sched.stories == ("STORY 1", "STORY 2", "STORY 3")
    assert sched.column_marks == ("C1", "C2", "C3")
    assert len(sched.columns) == 9  # 3 stories x 3 column marks





def test_member_dimensions_from_the_model_follow_its_units_and_no_cover_is_assumed():
    """Model sections are in model units: a kip-ft section (1.25 ft, cover 2 in) is drawn as 15 in with 2 in cover.
    A member without a cover in its design or section is not drawn with an assumed one."""
    from struct_core import ConcreteMaterial, Metadata, Project, RectangularSection, StructuralModel, parse_units
    from struct_core import BeamElement as CoreBeam, Node as CoreNode
    from struct_draw.adapters.struct_core_adapter import _extract_section_properties

    def project(cover):
        model = StructuralModel(
            nodes=[CoreNode(id=1, x=0.0, y=0.0), CoreNode(id=2, x=0.0, y=12.0)],
            materials=[ConcreteMaterial(id="C", fc=576.0, E=518000.0)],
            sections=[RectangularSection(id="COL", b=1.25, h=1.25, material_id="C", cover=cover)],
            elements=[CoreBeam(id="C1", start_node=1, end_node=2, section_id="COL")])
        return Project(model=model, metadata=Metadata(units=parse_units("kip, ft")))

    p = project(2.0 / 12.0)
    w, d, cover, length, metric = _extract_section_properties("C1", None, None, p.model, project=p)
    assert (w, d, cover, length, metric) == pytest.approx((15.0, 15.0, 2.0, 144.0, False))
    p = project(None)
    with pytest.raises(ValueError, match="cover"):
        _extract_section_properties("C1", None, None, p.model, project=p)


def test_metric_model_with_aci318_detailing_units_does_not_squeeze_columns_or_beams():
    """Verify that a metric model (kN, m) with ACI 318 detailing (which uses imperial units internally)
    extracts proper millimeter section dimensions (e.g. 300 mm x 400 mm) rather than converted inch dimensions (11.8 in x 15.7 in)."""
    from struct_core import ConcreteMaterial, Metadata, Project, RectangularSection, StructuralModel, parse_units, Units
    from struct_core import BeamElement as CoreBeam, Node as CoreNode
    from struct_draw.adapters.struct_core_adapter import _extract_section_properties, draw_from_core

    model = StructuralModel(
        nodes=[CoreNode(id=1, x=0.0, y=0.0, z=0.0), CoreNode(id=2, x=0.0, y=0.0, z=3.5)],
        materials=[ConcreteMaterial(id="C30", fc=30.0e3, E=30.0e6)],
        sections=[RectangularSection(id="COL_300x400", b=0.30, h=0.40, material_id="C30", cover=0.04)],
        elements=[CoreBeam(id="C1", start_node=1, end_node=2, section_id="COL_300x400")],
        units="kN, m",
    )
    p = Project(model=model, metadata=Metadata(units=Units(length="m", force="kN", time="s", mass="kg", temperature="C")))
    det_res = SimpleNamespace(
        units=Units(length="in", force="lbf", time="s", mass="slug", temperature="F"),
        bar_system="US",
        element_results={"C1": SimpleNamespace(bar_layout=None, bar_schedule=None, anchorage=None)},
    )
    p.detailing_results["ACI318_19"] = det_res
    w, d, cover, length, metric = _extract_section_properties("C1", det_res.element_results["C1"], None, p.model, project=p)
    assert metric is True
    assert (w, d, cover, length) == pytest.approx((300.0, 400.0, 40.0, 3500.0))

