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
    d_beam = SimpleNamespace(width=12.0, depth=20.0)

    # 2. Beam Profile (Continuous Beam)
    e_prof = ElementDetailingResult(element_id=102, member_type="beam_profile")
    d_prof = SimpleNamespace(width=14.0, depth=24.0, spans=[240.0, 300.0])

    # 3. Column
    e_col = ElementDetailingResult(element_id=103, member_type="column")
    d_col = SimpleNamespace(width=18.0, depth=18.0)

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


