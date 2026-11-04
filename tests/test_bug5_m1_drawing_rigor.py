"""
Verification tests for bug5 M1: Detailing drawings rigor, strict aci318 sourcing,
no fabricated seismic values, no unitless numbers or doubled quotes, and no fallbacks.
"""

from types import SimpleNamespace
import pytest

from struct_draw.core import (
    BeamData,
    ColumnData,
    FootingData,
    CombinedFootingData,
    GeometrySection,
    Rebar,
    Stirrup,
)
from struct_draw.core.units import DrawingUnit, format_length
from struct_draw.elements import beam, column, footing
from struct_draw.adapters.struct_core_adapter import (
    _element_to_beam_data,
    _element_to_column_data,
    _element_to_footing_data,
    _element_to_combined_footing_data,
    _normalize_stirrup_spacing,
)
from struct_core.detailing_result import (
    ElementDetailingResult,
    DetailingResult,
    BarLayout,
    RebarLayer,
    Bar,
    StirrupLayout,
)


class MockTarget:
    """Mock drawing target capturing entities."""
    def __init__(self):
        self.entities = []

    def add_line(self, *a, **k):
        self.entities.append(("line", a, k))

    def add_lwpolyline(self, *a, **k):
        self.entities.append(("poly", a, k))

    def add_text(self, *a, **k):
        self.entities.append(("text", a, k))

    def add_circle(self, *a, **k):
        self.entities.append(("circle", a, k))

    def add_leader(self, *a, **k):
        self.entities.append(("leader", a, k))

    def add_linear_dim(self, *a, **k):
        class Dim:
            def set_text(self, *a, **k): pass
            def render(self): pass
        self.entities.append(("dim", a, k))
        return Dim()

    def add_hatch(self, *a, **k):
        class Paths:
            def add_polyline_path(self, *a, **k): pass
        class Hatch:
            def __init__(self):
                self.paths = Paths()
            def set_pattern_fill(self, *a, **k): pass
        self.entities.append(("hatch", a, k))
        return Hatch()


def test_format_length_helper():
    """Verify format_length always includes units and never produces doubled quotes."""
    # Imperial
    s_in = format_length(8.5, is_metric=False)
    assert s_in == '8.5"'
    assert not s_in.endswith('""')

    # Metric
    s_mm = format_length(215.9, is_metric=True)
    assert s_mm == "216 mm"
    assert "mm" in s_mm


def test_beam_stirrups_metric_and_imperial_labels():
    """Beam designed with 8.5 in stirrups must show #3 @ 216 mm in metric and #3 @ 8.5\" in imperial."""
    b_data_metric = BeamData(
        name="B1",
        section=GeometrySection(width_in=300.0, depth_in=500.0, cover_in=40.0),
        length_in=5000.0,
        stirrups=Stirrup(size="#3", spacing_in=215.9),
        unit=DrawingUnit.MM,
    )
    t_m = MockTarget()
    beam.section_view(t_m, b_data_metric)
    texts_m = [e[1][0] for e in t_m.entities if e[0] == "text"]
    assert any("#3 @ 216 mm c/c" in txt for txt in texts_m)
    assert not any("T3" in txt for txt in texts_m)

    b_data_imp = BeamData(
        name="B1",
        section=GeometrySection(width_in=12.0, depth_in=20.0, cover_in=1.5),
        length_in=240.0,
        stirrups=Stirrup(size="#3", spacing_in=8.5),
        unit=DrawingUnit.IN,
    )
    t_imp = MockTarget()
    beam.section_view(t_imp, b_data_imp)
    texts_imp = [e[1][0] for e in t_imp.entities if e[0] == "text"]
    assert any('#3 @ 8.5" c/c' in txt for txt in texts_imp)
    assert not any('""' in txt for txt in texts_imp)


def test_column_elevation_seismic_detailing_strictly_drawn():
    """Column elevation must draw the exact designed seismic values with explicit units."""
    col = ColumnData(
        name="C1",
        section=GeometrySection(width_in=18.0, depth_in=18.0, cover_in=1.5),
        height_in=144.0,
        longitudinal_bars=(Rebar(mark="C1", size="#8", quantity=8),),
        stirrups=Stirrup(size="#4", spacing_in=4.0),
        lo=24.0,
        so=3.0,
        s_mid=6.0,
        s_joint=4.0,
        l_splice=48.0,
        splice_class="Class B",
        unit=DrawingUnit.IN,
    )
    t = MockTarget()
    column.elevation_view(t, col)
    texts = [e[1][0] for e in t.entities if e[0] == "text"]

    # Verify Lo region, central region, joint, and lap splice labels
    assert any('Lo REGION: #4 HOOPS @ 3" C/C' in txt for txt in texts)
    assert any('CENTRAL REGION: #4 TIES @ 6" C/C' in txt for txt in texts)
    assert any('#4 HOOPS @ 4" C/C' in txt and 'THROUGH JOINT' in txt for txt in texts)
    assert any('LAP SPLICE: Ld = 48"' in txt and 'CLASS B' in txt for txt in texts)
    # Ensure no unitless numbers like Ld = 26.0
    assert not any("Ld = 26.0\n" in txt for txt in texts)
    assert not any('""' in txt for txt in texts)


def test_footing_rebar_label_and_no_fabricated_column_ties():
    """Footing drawing must show '#5 (16 mm) @ 152 mm' in metric and NO fabricated column ties."""
    ftg_metric = FootingData.from_metric(
        name="F1",
        length=2000.0,
        width=2000.0,
        mid_thick=450.0,
        edge_thick=225.0,
        col_width=400.0,
        col_depth=400.0,
        bar_dia=16.0,
        bar_spacing=152.0,
        bar_size="#5",
        column_stirrups=None,  # No ties specified for footing pedestal
    )
    t = MockTarget()
    footing.section_view(t, ftg_metric)
    texts = [e[1][0] for e in t.entities if e[0] == "text"]

    # Main rebar callout must preserve #5 (16 mm) designation and exact spacing
    assert any("#5 (16 mm) @ 152 mm c/c" in txt for txt in texts)
    # Must NOT fabricate 8mm column stirrups
    assert not any("8mm dia" in txt for txt in texts)
    assert not any("column stirrups" in txt for txt in texts)


def test_missing_dimensions_raise_value_error():
    """Missing required dimensions in converters must raise ValueError."""
    # Footing missing thickness
    with pytest.raises(ValueError, match="missing thickness"):
        _element_to_footing_data(
            elem_id="F1",
            elem_detailing=SimpleNamespace(length_in=72.0, width_in=72.0, thickness_in=None),
            elem_design=None,
            model=None,
            unit=DrawingUnit.IN,
        )

    # Footing missing plan dimensions
    with pytest.raises(ValueError, match="missing plan dimensions"):
        _element_to_footing_data(
            elem_id="F1",
            elem_detailing=SimpleNamespace(length_in=None, width_in=None, thickness_in=18.0),
            elem_design=None,
            model=None,
            unit=DrawingUnit.IN,
        )

    # Combined footing missing thickness
    with pytest.raises(ValueError, match="missing thickness"):
        _element_to_combined_footing_data(
            elem_id="CF1",
            elem_detailing=SimpleNamespace(col_spacing_in=120.0, width_in=60.0, thickness_in=None),
            elem_design=None,
            model=None,
            unit=DrawingUnit.IN,
        )

    # Column elevation view missing seismic detailing
    col_missing = ColumnData(
        name="C_INCOMPLETE",
        section=GeometrySection(width_in=18.0, depth_in=18.0, cover_in=1.5),
        height_in=144.0,
        stirrups=Stirrup(size="#3", spacing_in=12.0),
    )
    with pytest.raises(ValueError, match="missing seismic detailing parameters"):
        column.elevation_view(MockTarget(), col_missing)


def test_normalize_stirrup_spacing_exact_conversions():
    """_normalize_stirrup_spacing must NOT floor-round to 25mm multiples or cap at 150mm."""
    # 8.5 in -> 216 mm (not rounded down to 200 mm)
    assert _normalize_stirrup_spacing(8.5, is_metric=True) == 216.0

    # 12.0 in -> 305 mm (not capped at 150 mm)
    assert _normalize_stirrup_spacing(12.0, is_metric=True, is_column=True) == 305.0

    # 6.0 in -> 152 mm
    assert _normalize_stirrup_spacing(6.0, is_metric=True) == 152.0

    # Imperial returns exact float
    assert _normalize_stirrup_spacing(8.5, is_metric=False) == 8.5
    assert _normalize_stirrup_spacing(12.0, is_metric=False) == 12.0

    # Negative / zero spacing raises
    with pytest.raises(ValueError, match="positive"):
        _normalize_stirrup_spacing(-5.0, is_metric=True)
