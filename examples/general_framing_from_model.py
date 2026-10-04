"""
Example: General Arrangement (GA) Drawing Generation directly from struct_core.StructuralModel.

Demonstrates:
1. Creating a StructuralModel (nodes, elements, sections, story elevations).
2. Generating a Floor Framing Plan (columns, beams, grid bubbles, dimensions).
3. Generating a Frame Elevation along a grid line (columns, beams, levels, grid bubbles).
4. Generating a Combined Plan & Elevation drawing sheet.
5. Saving all outputs to struct_draw/examples/output/.
"""

from pathlib import Path

from struct_core import (
    BeamElement,
    ElasticMaterial,
    Metadata,
    Node,
    Project,
    RectangularSection,
    StructuralModel,
    Units,
)
from struct_draw import (
    SCALE_1_100,
    SCALE_1_50,
    SCALE_1_8_IN,
    SCALE_1_4_IN,
    DrawingUnit,
    draw_frame_elevation_from_core,
    draw_framing_plan_from_core,
    draw_general_frame_from_core,
)


def build_sample_building_model() -> StructuralModel:
    """Build a 3D 3-bay x 2-bay, 3-story concrete building model in meters."""
    x_spans = [0.0, 6.0, 13.5, 19.5]  # Grids A, B, C, D (6m, 7.5m, 6m)
    y_spans = [0.0, 6.0, 12.0]        # Grids 1, 2, 3 (6m, 6m)
    z_levels = [0.0, 4.2, 7.8, 11.4]  # GL, FL1, FL2, ROOF (4.2m ground, 3.6m stories)

    nodes = []
    node_map = {}
    node_id = 1
    for k, z in enumerate(z_levels):
        for j, y in enumerate(y_spans):
            for i, x in enumerate(x_spans):
                nodes.append(Node(id=node_id, x=x, y=y, z=z))
                node_map[(i, j, k)] = node_id
                node_id += 1

    materials = [ElasticMaterial(id="CONC", E=2.5e7, nu=0.2, rho=2400.0)]
    sections = [
        RectangularSection(id="COL", name="C500x500", b=0.5, h=0.5),
        RectangularSection(id="BEAM_X", name="B350x650", b=0.35, h=0.65),
        RectangularSection(id="BEAM_Y", name="B300x550", b=0.3, h=0.55),
    ]

    elements = []
    elem_id = 1

    # Vertical Columns
    for k in range(len(z_levels) - 1):
        for j in range(len(y_spans)):
            for i in range(len(x_spans)):
                elements.append(
                    BeamElement(
                        id=f"COL_{elem_id}",
                        name=f"C{i+1}_{j+1}",
                        start_node=node_map[(i, j, k)],
                        end_node=node_map[(i, j, k + 1)],
                        material_id="CONC",
                        section_id="COL",
                    )
                )
                elem_id += 1

    # X-direction Beams
    for k in range(1, len(z_levels)):
        for j in range(len(y_spans)):
            for i in range(len(x_spans) - 1):
                elements.append(
                    BeamElement(
                        id=f"BX_{elem_id}",
                        name=f"BX{i+1}_{j+1}",
                        start_node=node_map[(i, j, k)],
                        end_node=node_map[(i + 1, j, k)],
                        material_id="CONC",
                        section_id="BEAM_X",
                    )
                )
                elem_id += 1

    # Y-direction Beams
    for k in range(1, len(z_levels)):
        for i in range(len(x_spans)):
            for j in range(len(y_spans) - 1):
                elements.append(
                    BeamElement(
                        id=f"BY_{elem_id}",
                        name=f"BY{i+1}_{j+1}",
                        start_node=node_map[(i, j, k)],
                        end_node=node_map[(i, j + 1, k)],
                        material_id="CONC",
                        section_id="BEAM_Y",
                    )
                )
                elem_id += 1

    return StructuralModel(
        nodes=nodes,
        elements=elements,
        materials=materials,
        sections=sections,
        story_elevations=z_levels,
    )


def run():
    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Building 3D office building StructuralModel (SI Metric)...")
    model = build_sample_building_model()
    project = Project(model=model)
    # Link explicit unit system to project metadata (meters & kilonewtons)
    project.metadata.title = "COMMERCIAL OFFICE BUILDING"
    project.metadata.units = Units(length="m", force="kN")

    # 1. Framing Plan at Level 1 (FL1) using standard 1:100 scale
    plan_out = out_dir / "framing_plan_fl1.dxf"
    print(f"Generating Framing Plan (FL1) at scale 1:100 -> {plan_out.name}...")
    res_plan = draw_framing_plan_from_core(
        project,
        story_level="FL1",
        title="COMMERCIAL OFFICE - LEVEL 1 FRAMING PLAN",
        scale=SCALE_1_100,  # Explicitly set 1:100 scale (or omit to use default 1:100)
        output_path=plan_out,
    )
    print(f"  -> Saved {plan_out.resolve()} (elements drawn: {res_plan['elements_drawn']})")

    # 2. Frame Elevation along Grid 1 using standard 1:50 scale
    elev_out = out_dir / "frame_elevation_grid1.dxf"
    print(f"Generating Frame Elevation (Grid 1) at scale 1:50 -> {elev_out.name}...")
    res_elev = draw_frame_elevation_from_core(
        project,
        grid_line="1",
        title="COMMERCIAL OFFICE - FRONT ELEVATION GRID 1",
        scale=SCALE_1_50,   # Standard 1:50 elevation scale
        output_path=elev_out,
    )
    print(f"  -> Saved {elev_out.resolve()} (elements drawn: {res_elev['elements_drawn']})")

    # 3. Combined Plan & Elevation Sheet with Coordinated Multi-Scale Views
    # (Plan automatically uses 1:100 while Elevation uses 1:50)
    combined_out = out_dir / "framing_combined_sheet.dxf"
    print(f"Generating Combined Plan (1:100) & Elevation (1:50) Sheet -> {combined_out.name}...")
    res_comb = draw_general_frame_from_core(
        project,
        view_mode="both",
        story_level="ROOF",
        title="COMMERCIAL OFFICE - GENERAL ARRANGEMENT",
        plan_scale=SCALE_1_100,
        elev_scale=SCALE_1_50,
        output_path=combined_out,
    )
    print(f"  -> Saved {combined_out.resolve()} (elements drawn: {res_comb['elements_drawn']})")

    # 4. Demonstrate US Customary Imperial Project (ft -> in, 1/4"=1'-0" scale)
    print("Generating US Customary Imperial Frame Elevation (1/4\"=1'-0\")...")
    imp_nodes = [
        Node(id=1, x=0.0, y=0.0, z=0.0),
        Node(id=2, x=24.0, y=0.0, z=0.0),   # 24 ft bay
        Node(id=3, x=0.0, y=0.0, z=14.0),   # 14 ft story height
        Node(id=4, x=24.0, y=0.0, z=14.0),
    ]
    imp_model = StructuralModel(
        nodes=imp_nodes,
        elements=[
            BeamElement(id="C1", name="C1", start_node=1, end_node=3, section_id="COL", material_id="STEEL"),
            BeamElement(id="C2", name="C2", start_node=2, end_node=4, section_id="COL", material_id="STEEL"),
            BeamElement(id="B1", name="B1", start_node=3, end_node=4, section_id="BEAM", material_id="STEEL"),
        ],
        materials=[ElasticMaterial(id="STEEL", E=29000.0, nu=0.3, rho=0.284)],
        sections=[
            RectangularSection(id="COL", name="W14x90", b=14.5, h=14.0),
            RectangularSection(id="BEAM", name="W21x50", b=6.5, h=20.8),
        ],
        story_elevations=[0.0, 14.0],
    )
    imp_project = Project(
        model=imp_model,
        metadata=Metadata(title="WAREHOUSE FRAME - IMPERIAL", units=Units(length="ft", force="kip")),
    )
    imp_out = out_dir / "frame_elevation_imperial_quarter_in.dxf"
    res_imp = draw_frame_elevation_from_core(
        imp_project,
        scale=SCALE_1_4_IN,  # 1/4" = 1'-0"
        title="WAREHOUSE FRAME ELEVATION (1/4\" = 1'-0\")",
        output_path=imp_out,
    )
    print(f"  -> Saved {imp_out.resolve()} (elements drawn: {res_imp['elements_drawn']})")


if __name__ == "__main__":
    run()
