"""
Unit tests for general frame drawing generation (plan, elevation, truss).
"""

import pytest
import ezdxf
from struct_draw.core.data import (
    FrameElevationData,
    FrameGridLine,
    FrameLevelLine,
    FrameMember,
    FrameNode,
    FramingPlanData,
    GeneralFrameData,
    TrussData,
)
from struct_draw.elements import general_frame
from struct_draw.backends import render, save_dxf
from struct_draw.adapters.struct_core_adapter import draw_general_frame_from_core


def test_general_frame_data_from_grid():
    """Test generating framing data from bay and story grid."""
    frame = GeneralFrameData.from_grid(
        name="TEST-FRAME",
        bays=(240.0, 240.0),
        story_heights=(144.0, 120.0),
        col_width=16.0,
        col_depth=16.0,
        beam_width=12.0,
        beam_depth=20.0,
        title="2-BAY 2-STORY FRAME",
    )

    assert len(frame.nodes) == 9  # 3 cols x 3 levels
    assert len(frame.members) == 10  # 6 cols + 4 beams
    assert len(frame.grid_x) == 3
    assert len(frame.levels) == 3


def test_elevation_view_rendering():
    """Test drawing the elevation view with outline geometry."""
    doc = ezdxf.new("R2018")
    msp = doc.modelspace()

    frame = GeneralFrameData.from_grid(
        name="ELEV-FRAME",
        bays=(240.0, 288.0),
        story_heights=(144.0, 120.0),
        col_width=18.0,
        col_depth=18.0,
        beam_width=14.0,
        beam_depth=24.0,
        is_metric=False,
    )

    res = general_frame.elevation_view(msp, frame, origin=(0.0, 0.0), scale=0.02)
    bounds = res["bounding_box"]
    assert bounds[0] <= bounds[2]
    assert bounds[1] <= bounds[3]

    entities = list(msp)
    assert len(entities) > 20
    # Check that outlines and dimensions are present
    types = {e.dxftype() for e in entities}
    assert "LWPOLYLINE" in types or "LINE" in types
    assert "TEXT" in types or "MTEXT" in types


def test_plan_view_rendering():
    """Test drawing framing plan view with grid and column blocks."""
    doc = ezdxf.new("R2018")
    msp = doc.modelspace()

    frame = GeneralFrameData.from_grid(
        name="PLAN-FRAME",
        bays=(240.0, 240.0),
        story_heights=(144.0,),
        col_width=16.0,
        col_depth=16.0,
        beam_width=12.0,
        beam_depth=18.0,
    )

    bounds = general_frame.plan_view(msp, frame, origin=(0.0, 0.0), level_label="L1", scale=0.02)
    entities = list(msp)
    assert len(entities) > 10


def test_truss_view_rendering():
    """Test generating and drawing various truss types."""
    doc = ezdxf.new("R2018")
    msp = doc.modelspace()

    # Pratt truss
    pratt = TrussData.pratt(span_in=720.0, height_in=96.0, panels=6, title="PRATT ROOF TRUSS")
    b1 = general_frame.truss_view(msp, pratt, origin=(0.0, 0.0))
    assert "bounding_box" in b1
    assert pratt.panels == 6

    # Warren truss
    warren = TrussData.warren(span_in=600.0, height_in=72.0, panels=6, title="WARREN TRUSS")
    b2 = general_frame.truss_view(msp, warren, origin=(0.0, -200.0))
    assert "bounding_box" in b2
    assert warren.panels == 6

    # Pitched / Howe truss
    pitched = TrussData.pitched(span_in=480.0, height_in=120.0, panels=4, title="PITCHED ROOF TRUSS")
    b3 = general_frame.truss_view(msp, pitched, origin=(0.0, -400.0))
    assert "bounding_box" in b3
    assert pitched.panels == 4

    assert len(list(msp)) > 40


def test_backend_render_dispatcher():
    """Test top-level backend render() with GeneralFrameData and TrussData."""
    frame = GeneralFrameData.from_grid(
        name="BF-FRAME",
        bays=(300.0, 300.0),
        story_heights=(150.0,),
    )
    res_frame = render(frame)
    assert res_frame.doc is not None
    assert len(list(res_frame.doc.modelspace())) > 0

    truss = TrussData.howe(span_in=480.0, height_in=80.0, panels=4)
    res_truss = render(truss)
    assert res_truss.doc is not None
    assert len(list(res_truss.doc.modelspace())) > 0


def test_draw_general_frame_from_core_adapter():
    """Test adapter function draw_general_frame_from_core with custom model structure."""
    class MockNode:
        def __init__(self, id, x, y, z=0.0):
            self.id = id
            self.x = x
            self.y = y
            self.z = z

    class MockMember:
        def __init__(self, id, start_node, end_node, member_type="beam", width=12.0, depth=20.0):
            self.id = id
            self.start_node = start_node
            self.end_node = end_node
            self.member_type = member_type
            self.width = width
            self.depth = depth

    class MockModel:
        def __init__(self):
            self.name = "PORTAL-FRAME"
            self.nodes = {
                1: MockNode(1, 0.0, 0.0),
                2: MockNode(2, 240.0, 0.0),
                3: MockNode(3, 0.0, 144.0),
                4: MockNode(4, 240.0, 144.0),
            }
            self.elements = {
                1: MockMember(1, 1, 3, member_type="column", width=16.0, depth=16.0),
                2: MockMember(2, 2, 4, member_type="column", width=16.0, depth=16.0),
                3: MockMember(3, 3, 4, member_type="beam", width=12.0, depth=20.0),
            }
            self.grids = {"A": 0.0, "B": 240.0}
            self.levels = {"GL": 0.0, "L1": 144.0}

    model = MockModel()
    res = draw_general_frame_from_core(model, view_mode="both")

    assert res["drawing"] is not None
    assert res["elements_drawn"] == 3
    msp = res["drawing"].modelspace()
    assert len(list(msp)) > 15
