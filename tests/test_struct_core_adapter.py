"""
Unit tests for struct_draw.adapters.struct_core_adapter.
"""

import ezdxf
import pytest
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

    # 2. Render DXF
    res = draw_from_core(detailing_result)

    assert "drawing" in res
    assert hasattr(res["drawing"], "modelspace")
    assert res["elements_drawn"] == 1
    assert 1 in res["data"]

    # Verify DXF entities in modelspace
    msp = res["drawing"].modelspace()
    assert len(list(msp)) > 0
