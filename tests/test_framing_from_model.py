"""
Tests for General Arrangement Framing Drawing generation from struct_core.StructuralModel.
"""

from pathlib import Path
import pytest
from struct_core import (
    BeamElement,
    ElasticMaterial,
    Node,
    Project,
    RectangularSection,
    StructuralModel,
    Support,
)
from struct_draw import (
    GeneralFrameData,
    create_general_frame_data_from_model,
    draw_frame_elevation_from_core,
    draw_framing_plan_from_core,
    draw_from_core,
    draw_general_frame_from_core,
    save_dxf,
)


def _make_2d_portal_model() -> StructuralModel:
    """Create a 2D 1-bay 1-story frame model in meters."""
    nodes = [
        Node(id=1, x=0.0, y=0.0, z=0.0),
        Node(id=2, x=6.0, y=0.0, z=0.0),
        Node(id=3, x=0.0, y=3.5, z=0.0),
        Node(id=4, x=6.0, y=3.5, z=0.0),
    ]
    materials = [ElasticMaterial(id="CONC", E=2.5e7, nu=0.2, rho=2400.0)]
    sections = [
        RectangularSection(id="COL", material_id="CONC", name="C400x400", b=0.4, h=0.4),
        RectangularSection(id="BEAM", material_id="CONC", name="B300x500", b=0.3, h=0.5),
    ]
    elements = [
        BeamElement(id="C1", name="C1", start_node=1, end_node=3, section_id="COL"),
        BeamElement(id="C2", name="C2", start_node=2, end_node=4, section_id="COL"),
        BeamElement(id="B1", name="B1", start_node=3, end_node=4, section_id="BEAM"),
    ]
    supports = [Support.fixed(node_id=1), Support.fixed(node_id=2)]
    return StructuralModel(
        nodes=nodes,
        elements=elements,
        materials=materials,
        sections=sections,
        supports=supports,
        story_elevations=[0.0, 3.5],
    )


def _make_3d_frame_model() -> StructuralModel:
    """Create a 3D 2-bay x 1-bay, 2-story building frame in meters."""
    # X: 0.0, 6.0, 12.0 (Grids A, B, C)
    # Y: 0.0, 5.0 (Grids 1, 2)
    # Z: 0.0, 3.5, 7.0 (GL, FL1, ROOF)
    x_coords = [0.0, 6.0, 12.0]
    y_coords = [0.0, 5.0]
    z_coords = [0.0, 3.5, 7.0]

    nodes = []
    node_map = {}
    node_id = 1
    for k, z in enumerate(z_coords):
        for j, y in enumerate(y_coords):
            for i, x in enumerate(x_coords):
                nodes.append(Node(id=node_id, x=x, y=y, z=z))
                node_map[(i, j, k)] = node_id
                node_id += 1

    materials = [ElasticMaterial(id="CONC", E=2.5e7, nu=0.2, rho=2400.0)]
    sections = [
        RectangularSection(id="COL", material_id="CONC", name="C450x450", b=0.45, h=0.45),
        RectangularSection(id="BEAM", material_id="CONC", name="B300x600", b=0.3, h=0.6),
    ]

    elements = []
    elem_id = 1

    # Columns (between story levels)
    for k in range(len(z_coords) - 1):
        for j in range(len(y_coords)):
            for i in range(len(x_coords)):
                elements.append(
                    BeamElement(
                        id=f"COL_{elem_id}",
                        name=f"C{i+1}_{j+1}_{k+1}",
                        start_node=node_map[(i, j, k)],
                        end_node=node_map[(i, j, k + 1)],
                        section_id="COL",
                    )
                )
                elem_id += 1

    # X-direction Beams
    for k in range(1, len(z_coords)):
        for j in range(len(y_coords)):
            for i in range(len(x_coords) - 1):
                elements.append(
                    BeamElement(
                        id=f"BEAM_X_{elem_id}",
                        name=f"BX{i+1}_{j+1}_L{k}",
                        start_node=node_map[(i, j, k)],
                        end_node=node_map[(i + 1, j, k)],
                        section_id="BEAM",
                    )
                )
                elem_id += 1

    # Y-direction Beams
    for k in range(1, len(z_coords)):
        for i in range(len(x_coords)):
            for j in range(len(y_coords) - 1):
                elements.append(
                    BeamElement(
                        id=f"BEAM_Y_{elem_id}",
                        name=f"BY{i+1}_{j+1}_L{k}",
                        start_node=node_map[(i, j, k)],
                        end_node=node_map[(i, j + 1, k)],
                        section_id="BEAM",
                    )
                )
                elem_id += 1

    return StructuralModel(
        nodes=nodes,
        elements=elements,
        materials=materials,
        sections=sections,
        story_elevations=z_coords,
    )


def test_2d_frame_to_general_frame_data():
    """Verify 2D frame model produces properly scaled GeneralFrameData."""
    model = _make_2d_portal_model()
    frame_data = create_general_frame_data_from_model(model, view_mode="elevation")

    assert isinstance(frame_data, GeneralFrameData)
    assert frame_data.is_metric is True
    # Verify coordinates scaled from meters to mm (6.0m -> 6000.0mm, 3.5m -> 3500.0mm)
    assert len(frame_data.grid_x) == 2
    assert frame_data.grid_x[0].coord == pytest.approx(0.0)
    assert frame_data.grid_x[1].coord == pytest.approx(6000.0)
    assert frame_data.grid_x[0].label == "A"
    assert frame_data.grid_x[1].label == "B"

    # Verify levels (0 -> GL, 3500 -> ROOF)
    assert len(frame_data.levels) == 2
    assert frame_data.levels[0].elevation == pytest.approx(0.0)
    assert frame_data.levels[1].elevation == pytest.approx(3500.0)

    # Verify members classification
    cols = [m for m in frame_data.members if m.member_type == "column"]
    beams = [m for m in frame_data.members if m.member_type == "beam"]
    assert len(cols) == 2
    assert len(beams) == 1
    # Check section dimensions in mm (0.4m -> 400mm, 0.3m -> 300mm, 0.5m -> 500mm)
    assert cols[0].width_in == pytest.approx(400.0)
    assert cols[0].depth_in == pytest.approx(400.0)
    assert beams[0].width_in == pytest.approx(300.0)
    assert beams[0].depth_in == pytest.approx(500.0)


def test_3d_frame_plan_filtering():
    """Verify 3D frame model allows filtering framing plans by story level."""
    model = _make_3d_frame_model()

    # Plan at Roof (elevation 7000 mm)
    roof_plan = create_general_frame_data_from_model(model, view_mode="plan", story_level="ROOF")
    assert roof_plan.view_mode == "plan"
    assert "ROOF" in roof_plan.title
    assert len(roof_plan.grid_x) == 3  # Grids A, B, C
    assert len(roof_plan.grid_y) == 2  # Grids 1, 2

    # Roof level beams: 4 beams in X, 3 beams in Y = 7 beams
    beams = [m for m in roof_plan.members if m.member_type == "beam"]
    assert len(beams) == 7

    # Plan at FL1 (elevation 3500 mm)
    fl1_plan = create_general_frame_data_from_model(model, view_mode="plan", story_level="FL1")
    assert "FL1" in fl1_plan.title
    fl1_beams = [m for m in fl1_plan.members if m.member_type == "beam"]
    assert len(fl1_beams) == 7


def test_3d_frame_elevation_grid_filtering():
    """Verify 3D frame model allows filtering frame elevations by grid line."""
    model = _make_3d_frame_model()

    # Elevation along Grid 1 (front elevation along Y=0)
    elev_g1 = create_general_frame_data_from_model(model, view_mode="elevation", grid_line="1")
    assert elev_g1.view_mode == "elevation"
    assert "GRID 1" in elev_g1.title
    # Grids along X: A, B, C
    assert len(elev_g1.grid_x) == 3
    # Story levels: GL, FL1, ROOF
    assert len(elev_g1.levels) == 3

    # Along Grid 1: 3 columns x 2 stories = 6 columns, 2 bays x 2 stories = 4 beams
    cols = [m for m in elev_g1.members if m.member_type == "column"]
    beams = [m for m in elev_g1.members if m.member_type == "beam"]
    assert len(cols) == 6
    assert len(beams) == 4


def test_draw_general_frame_from_core_both_modes(tmp_path):
    """Verify draw_general_frame_from_core produces a combined plan & elevation DXF."""
    model = _make_3d_frame_model()
    out_file = tmp_path / "combined_framing.dxf"

    res = draw_general_frame_from_core(
        model,
        view_mode="both",
        output_path=out_file,
    )

    assert out_file.exists()
    assert out_file.stat().st_size > 1000
    assert "drawing" in res
    assert "plan" in res["data"]
    assert "elevation" in res["data"]
    assert res["elements_drawn"] == len(model.elements)


def test_draw_framing_plan_and_elevation_entrypoints(tmp_path):
    """Verify convenience entrypoints draw_framing_plan_from_core and draw_frame_elevation_from_core."""
    model = _make_3d_frame_model()
    project = Project(model=model)

    plan_dxf = tmp_path / "plan.dxf"
    res_plan = draw_framing_plan_from_core(project, story_level="ROOF", output_path=plan_dxf)
    assert plan_dxf.exists()
    assert "plan" in res_plan["data"]

    elev_dxf = tmp_path / "elev.dxf"
    res_elev = draw_frame_elevation_from_core(project, grid_line="1", output_path=elev_dxf)
    assert elev_dxf.exists()
    assert "elevation" in res_elev["data"]


def test_draw_from_core_general_framing_fallback():
    """Verify draw_from_core dispatches to GA framing when view_type='plan' or detailing is absent."""
    model = _make_2d_portal_model()
    project = Project(model=model)

    res = draw_from_core(project, view_type="plan")
    assert res["drawing"] is not None
    assert "plan" in res["data"]


def test_draw_general_frame_3d_both_orthogonal_elevations(tmp_path):
    """Verify 3D models produce framing plan and elevations in both orthogonal directions (X and Y grids)."""
    model = _make_3d_frame_model()
    out_file = tmp_path / "orthogonal_framing.dxf"

    res = draw_general_frame_from_core(
        model,
        view_mode="both",
        output_path=out_file,
    )

    assert out_file.exists()
    assert "plan" in res["data"]
    assert "elevation" in res["data"]
    assert "elevation_transverse" in res["data"]
    assert "elevation_x" in res["views"]
    assert "elevation_y" in res["views"]
    assert res["views"]["elevation_x"] is not None
    assert res["views"]["elevation_y"] is not None

