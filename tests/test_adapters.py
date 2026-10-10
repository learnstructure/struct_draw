"""Unit tests for struct_draw.adapters.aci318."""

from __future__ import annotations

from types import SimpleNamespace

from struct_draw.adapters.aci318 import (
    from_beam_result,
    from_column_result,
    from_combined_footing_result,
    from_isolated_footing_result,
    from_slab_result,
    from_staircase_result,
)
from struct_draw.core.data import (
    BeamData,
    ColumnData,
    CombinedFootingData,
    FootingData,
    IsolatedFootingData,
    SlabData,
    StaircaseData,
)


def test_from_beam_result() -> None:
    design = SimpleNamespace(
        name="B101",
        length=280.0,
        section=SimpleNamespace(width=14.0, depth=28.0, cover=1.5),
        shear=SimpleNamespace(size="#4", spacing=8.0, legs=2),
    )
    detailing = SimpleNamespace(
        top_bars=[SimpleNamespace(mark="T1", size="#6", quantity=3, length=270.0)],
        bottom_bars=[SimpleNamespace(mark="B1", size="#8", quantity=2, length=270.0)],
        schedule_rows=[
            SimpleNamespace(mark="T1", size="#6", quantity=3, length=270.0, remarks="TOP"),
            SimpleNamespace(mark="B1", size="#8", quantity=2, length=270.0, remarks="BOT"),
        ],
    )
    result = from_beam_result((design, detailing))
    assert isinstance(result, BeamData)
    assert result.name == "B101"
    assert result.section.width_in == 14.0
    assert result.section.depth_in == 28.0
    assert len(result.top_bars) == 1
    assert result.top_bars[0].mark == "T1"
    assert len(result.bottom_bars) == 1
    assert result.bottom_bars[0].size == "#8"
    assert len(result.schedule) == 2


def test_from_isolated_footing_result() -> None:
    design = SimpleNamespace(
        name="F2",
        length=72.0,
        width=72.0,
        mid_thickness=18.0,
        edge_thickness=10.0,
        column_width=16.0,
        column_depth=16.0,
        bar_dia=0.625,
        bar_spacing=6.0,
    )
    result = from_isolated_footing_result(design)
    assert isinstance(result, IsolatedFootingData)
    assert isinstance(result, FootingData)
    assert FootingData is IsolatedFootingData
    assert result.name == "F2"
    assert result.length_in == 72.0
    assert result.width_in == 72.0
    assert result.mid_thickness_in == 18.0


def test_from_combined_footing_result() -> None:
    design = SimpleNamespace(
        name="CF1",
        length=16.0,  # 16 ft = 192 in
        width=5.0,    # 5 ft = 60 in
        thickness=24.0,
        col_spacing=96.0,
        proj_left=48.0,
        col1_width=16.0,
        col1_depth=16.0,
        col2_width=18.0,
        col2_depth=18.0,
        cover=3.0,
        bar_dia=1.0,
        bar_spacing=8.0,
        top_bar_dia=1.0,
        top_bar_spacing=8.0,
    )
    result = from_combined_footing_result(design)
    assert isinstance(result, CombinedFootingData)
    assert result.name == "CF1"
    assert result.width_in == 60.0
    assert result.thickness_in == 24.0
    assert result.col_spacing_in == 96.0
    assert result.proj_left_in == 48.0
    assert result.proj_right_in == 48.0  # 192 - 48 - 96 = 48
    assert result.col1_width_in == 16.0
    assert result.col2_width_in == 18.0


def test_from_column_result() -> None:
    design = SimpleNamespace(
        name="C1",
        height=144.0,
        section=SimpleNamespace(width=18.0, depth=18.0, cover=1.5),
    )
    result = from_column_result(design)
    assert isinstance(result, ColumnData)
    assert result.name == "C1"
    assert result.height_in == 144.0


def test_from_staircase_result() -> None:
    design = SimpleNamespace(
        name="ST1",
        flight_width=54.0,
        flight_length=132.0,
        riser_height=6.5,
        tread_depth=11.5,
    )
    result = from_staircase_result(design)
    assert isinstance(result, StaircaseData)
    assert result.name == "ST1"
    assert result.flight_width_in == 54.0
    assert result.riser_height_in == 6.5


def test_from_slab_result() -> None:
    design = SimpleNamespace(
        name="S1",
        length=300.0,
        width=180.0,
        thickness=8.0,
    )
    result = from_slab_result(design)
    assert isinstance(result, SlabData)
    assert result.name == "S1"
    assert result.length_in == 300.0
    assert result.thickness_in == 8.0


def test_from_isolated_footing_result_tuple() -> None:
    coord = SimpleNamespace(
        member_id="FTG-99",
        col_c1=18.0,
        col_c2=18.0,
        thickness=20.0,
        cover=3.0,
    )
    design = SimpleNamespace(
        length=8.0,
        width=8.0,
        detailing=SimpleNamespace(
            bars=[SimpleNamespace(bar_size="#7", count=8)],
        ),
    )
    res = from_isolated_footing_result((coord, design))
    assert isinstance(res, IsolatedFootingData)
    assert res.name == "FTG-99"
    assert res.length_in == 96.0
    assert res.width_in == 96.0
    assert res.mid_thickness_in == 20.0
    assert res.column_width_in == 18.0
    assert res.bar_dia_in == 0.875


def test_from_combined_footing_result_tuple() -> None:
    coord = SimpleNamespace(
        member_id="CF-99",
        col1_c1=16.0,
        col1_c2=16.0,
        col2_c1=20.0,
        col2_c2=20.0,
        column_spacing_ft=10.0,
        cantilever_col1_ft=2.0,
        thickness=28.0,
        cover=3.0,
    )
    design = SimpleNamespace(
        length=15.0,  # 15 ft = 180 in
        width=6.0,   # 6 ft = 72 in
        detailing=SimpleNamespace(
            bars=[
                SimpleNamespace(location="top_longitudinal", bar_size="#9", count=6),
                SimpleNamespace(location="bottom_longitudinal", bar_size="#8", count=7),
            ],
        ),
    )
    res = from_combined_footing_result((coord, design))
    assert isinstance(res, CombinedFootingData)
    assert res.name == "CF-99"
    assert res.col_spacing_in == 120.0
    assert res.proj_left_in == 24.0
    assert res.proj_right_in == 36.0  # 180 - 120 - 24
    assert res.width_in == 72.0
    assert res.thickness_in == 28.0
    assert res.top_bar_dia_in == 1.125
    assert res.bar_dia_in == 1.0

