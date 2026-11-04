"""Tests for unit awareness, drawing scale factors, and paper-space drafting standards in struct_draw."""

from __future__ import annotations

import math
import pytest
from pathlib import Path

from struct_core import (
    BeamElement,
    ElasticMaterial,
    Metadata,
    Node,
    Project,
    RectangularSection,
    StructuralModel,
    Support,
)
from struct_core.units import Units

from struct_draw.core.units import (
    DrawingScale,
    DrawingUnit,
    SCALE_1_100,
    SCALE_1_50,
    SCALE_1_25,
    SCALE_1_20,
    SCALE_1_10,
    SCALE_1_8_IN,
    SCALE_1_4_IN,
    SCALE_1_IN,
    drawing_unit_from_core,
)
from struct_draw.style.annotation_config import AnnotationConfig, DEFAULT_ANNOTATION_CONFIG
from struct_draw.style.dimension_styles import default_registry
from struct_draw.adapters import draw_general_frame_from_core
from struct_draw.elements import beam, beam_profile
from struct_draw.core.data import BeamData, BeamProfileData


class TestDrawingUnits:
    def test_drawing_unit_enum_and_conversions(self):
        assert DrawingUnit.MM.scale_to_mm == 1.0
        assert DrawingUnit.CM.scale_to_mm == 10.0
        assert DrawingUnit.M.scale_to_mm == 1000.0
        assert DrawingUnit.IN.scale_to_mm == 25.4
        assert DrawingUnit.FT.scale_to_mm == 304.8

        assert DrawingUnit.from_str("mm") == DrawingUnit.MM
        assert DrawingUnit.from_str("METER") == DrawingUnit.M
        assert DrawingUnit.from_str("inch") == DrawingUnit.IN
        assert DrawingUnit.from_str("ft") == DrawingUnit.FT

    def test_format_dimension(self):
        # Metric mm
        assert DrawingUnit.MM.format_dimension(3500.0) == "3500"
        # Metric m
        assert DrawingUnit.M.format_dimension(3.5) == "3.5m"
        # Imperial inches
        assert DrawingUnit.IN.format_dimension(12.0) == '12"'
        assert DrawingUnit.IN.format_dimension(12.5) == '12.5"'
        # Imperial feet-inches
        assert DrawingUnit.FT.format_dimension(10.5) == "10'-6\""
        assert DrawingUnit.FT.format_dimension(10.0) == "10'-0\""


class TestDrawingScales:
    def test_metric_and_imperial_scales(self):
        s100 = DrawingScale.metric(100)
        assert s100.ratio == 100.0
        assert s100.name == "1:100"
        assert s100.is_metric is True

        s_quarter = DrawingScale.imperial('1/4"=1\'-0"')
        assert s_quarter.ratio == 48.0
        assert s_quarter.is_metric is False

        # From string
        s_parsed = DrawingScale.from_str("1:50")
        assert s_parsed.ratio == 50.0

        s_parsed_imp = DrawingScale.from_str('1/8"=1\'-0"')
        assert s_parsed_imp.ratio == 96.0

    def test_drawing_unit_from_core_metric(self):
        proj = Project(metadata=Metadata(title="Metric Test", units=Units(length="m", force="kN")))
        target_unit, coord_factor, section_factor = drawing_unit_from_core(proj.metadata.units)

        assert target_unit == DrawingUnit.MM
        assert coord_factor == 1000.0  # m -> mm
        assert section_factor == 1000.0  # m -> mm

    def test_drawing_unit_from_core_us_customary(self):
        proj = Project(metadata=Metadata(title="Imperial Test", units=Units(length="ft", force="kip")))
        target_unit, coord_factor, section_factor = drawing_unit_from_core(proj.metadata.units)

        assert target_unit == DrawingUnit.IN
        assert coord_factor == 12.0  # ft -> in
        assert section_factor == 1.0  # already inches


class TestAnnotationConfigPlottedStandards:
    """Verify that paper-space print dimensions match structural drafting standards:
    - Dimensions: ~2.0 mm on paper
    - General text / annotations: ~3.0 mm on paper
    - View titles: ~5.0 mm on paper
    - Grid bubbles: ~4.0 mm radius on paper
    - Dimension offset: ~6.0 mm on paper
    """

    def test_metric_annotation_heights(self):
        cfg = DEFAULT_ANNOTATION_CONFIG

        # At 1:100 in mm (plan view)
        assert math.isclose(cfg.dim_text_height(SCALE_1_100, DrawingUnit.MM), 200.0, rel_tol=1e-5)
        assert math.isclose(cfg.text_height(SCALE_1_100, DrawingUnit.MM), 300.0, rel_tol=1e-5)
        assert math.isclose(cfg.title_height(SCALE_1_100, DrawingUnit.MM), 500.0, rel_tol=1e-5)
        assert math.isclose(cfg.bubble_radius(SCALE_1_100, DrawingUnit.MM), 400.0, rel_tol=1e-5)
        assert math.isclose(cfg.dim_offset(SCALE_1_100, DrawingUnit.MM), 600.0, rel_tol=1e-5)

        # At 1:50 in mm (elevation view)
        assert math.isclose(cfg.dim_text_height(SCALE_1_50, DrawingUnit.MM), 100.0, rel_tol=1e-5)
        assert math.isclose(cfg.text_height(SCALE_1_50, DrawingUnit.MM), 150.0, rel_tol=1e-5)
        assert math.isclose(cfg.title_height(SCALE_1_50, DrawingUnit.MM), 250.0, rel_tol=1e-5)

        # At 1:20 in mm (detailing view)
        assert math.isclose(cfg.dim_text_height(SCALE_1_20, DrawingUnit.MM), 40.0, rel_tol=1e-5)
        assert math.isclose(cfg.text_height(SCALE_1_20, DrawingUnit.MM), 60.0, rel_tol=1e-5)
        assert math.isclose(cfg.title_height(SCALE_1_20, DrawingUnit.MM), 100.0, rel_tol=1e-5)

    def test_imperial_annotation_heights(self):
        cfg = DEFAULT_ANNOTATION_CONFIG

        # At 1/4"=1'-0" in inches (ratio = 48)
        # 2 mm / 25.4 * 48 = 3.779527...
        expected_dim_th = (2.0 / 25.4) * 48.0
        expected_text_th = (3.0 / 25.4) * 48.0
        expected_title_th = (5.0 / 25.4) * 48.0

        assert math.isclose(cfg.dim_text_height(SCALE_1_4_IN, DrawingUnit.IN), expected_dim_th, rel_tol=1e-4)
        assert math.isclose(cfg.text_height(SCALE_1_4_IN, DrawingUnit.IN), expected_text_th, rel_tol=1e-4)
        assert math.isclose(cfg.title_height(SCALE_1_4_IN, DrawingUnit.IN), expected_title_th, rel_tol=1e-4)

    def test_flexible_scale_inputs(self):
        cfg = DEFAULT_ANNOTATION_CONFIG
        # Pass float ratio
        th_from_float = cfg.text_height(scale=0.02, unit="mm")  # 1/50
        assert math.isclose(th_from_float, 150.0, rel_tol=1e-5)

        # Pass integer ratio
        th_from_int = cfg.text_height(scale=50, unit="mm")
        assert math.isclose(th_from_int, 150.0, rel_tol=1e-5)

        # Pass string
        th_from_str = cfg.text_height(scale="1:50", unit="mm")
        assert math.isclose(th_from_str, 150.0, rel_tol=1e-5)


class TestDXFDrawingIntegration:
    @pytest.fixture
    def sample_metric_project(self):
        nodes = [
            Node(id=1, x=0.0, y=0.0, z=0.0),
            Node(id=2, x=6.0, y=0.0, z=0.0),
            Node(id=3, x=0.0, y=0.0, z=3.5),
            Node(id=4, x=6.0, y=0.0, z=3.5),
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
        model = StructuralModel(
            nodes=nodes,
            elements=elements,
            materials=materials,
            sections=sections,
            supports=supports,
            story_elevations=[0.0, 3.5],
        )
        return Project(
            metadata=Metadata(title="Metric Office Building", units=Units(length="m", force="kN")),
            model=model,
        )

    def test_draw_general_frame_metric_scaled(self, sample_metric_project, tmp_path):
        out_dxf = tmp_path / "metric_frame_1_100.dxf"
        res = draw_general_frame_from_core(
            sample_metric_project,
            view_mode="both",
            scale="1:100",
            output_path=str(out_dxf),
        )

        assert out_dxf.exists()
        doc = res["drawing"]
        assert doc is not None

        # Verify dimension styles registered in doc
        dim_styles = [ds.dxf.name for ds in doc.dimstyles]
        assert any("DIM_" in name for name in dim_styles)

        # Check modelspace entities
        msp = doc.modelspace()
        texts = [e for e in msp if e.dxftype() in ("TEXT", "MTEXT")]
        assert len(texts) > 0

    def test_draw_general_frame_imperial_scaled(self, tmp_path):
        nodes = [
            Node(id=1, x=0.0, y=0.0, z=0.0),
            Node(id=2, x=20.0, y=0.0, z=0.0),
            Node(id=3, x=0.0, y=0.0, z=12.0),
            Node(id=4, x=20.0, y=0.0, z=12.0),
        ]
        materials = [ElasticMaterial(id="STEEL", E=29000.0, nu=0.3, rho=0.284)]
        sections = [
            RectangularSection(id="COL", material_id="STEEL", name="W12x26", b=6.5, h=12.2),  # in inches
            RectangularSection(id="BEAM", material_id="STEEL", name="W16x31", b=5.5, h=15.9),
        ]
        elements = [
            BeamElement(id="C1", name="C1", start_node=1, end_node=3, section_id="COL"),
            BeamElement(id="C2", name="C2", start_node=2, end_node=4, section_id="COL"),
            BeamElement(id="B1", name="B1", start_node=3, end_node=4, section_id="BEAM"),
        ]
        supports = [Support.fixed(node_id=1), Support.fixed(node_id=2)]
        model = StructuralModel(
            nodes=nodes,
            elements=elements,
            materials=materials,
            sections=sections,
            supports=supports,
            story_elevations=[0.0, 12.0],
        )

        project = Project(
            metadata=Metadata(title="Imperial Warehouse", units=Units(length="ft", force="kip")),
            model=model,
        )

        out_dxf = tmp_path / "imperial_frame_quarter_in.dxf"
        res = draw_general_frame_from_core(
            project,
            view_mode="both",
            scale='1/4"=1\'-0"',
            output_path=str(out_dxf),
        )

        assert out_dxf.exists()
        assert res["elements_drawn"] == 3

    def test_beam_profile_with_scale_and_unit(self, tmp_path):
        data = BeamProfileData(
            name="B101",
            spans_in=(6000.0,),
            beam_width_in=300.0,
            beam_depth_in=500.0,
            scale=SCALE_1_25,
            unit=DrawingUnit.MM,
        )
        assert data.scale == SCALE_1_25
        assert data.unit == DrawingUnit.MM
        assert data.is_metric is True

    def test_default_scale_for_view(self):
        from struct_draw import default_scale_for_view

        # Metric view defaults
        assert default_scale_for_view("plan", is_metric=True) == SCALE_1_100
        assert default_scale_for_view("elevation", is_metric=True) == SCALE_1_50
        assert default_scale_for_view("beam_profile", is_metric=True) == SCALE_1_25
        assert default_scale_for_view("footing", is_metric=True) == SCALE_1_25
        assert default_scale_for_view("staircase", is_metric=True) == SCALE_1_25
        assert default_scale_for_view("section", is_metric=True) == SCALE_1_20
        assert default_scale_for_view("detail", is_metric=True) == SCALE_1_20

        # Imperial view defaults
        assert default_scale_for_view("plan", is_metric=False) == SCALE_1_8_IN
        assert default_scale_for_view("elevation", is_metric=False) == SCALE_1_4_IN
        assert default_scale_for_view("section", is_metric=False) == SCALE_1_IN
        assert default_scale_for_view("detail", is_metric=False) == SCALE_1_IN
