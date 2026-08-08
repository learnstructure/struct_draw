"""Unit tests for struct_draw.adapters.aci318."""

from __future__ import annotations

from types import SimpleNamespace

from struct_draw.adapters.aci318 import (
    from_beam_result,
    from_column_result,
    from_footing_result,
    from_slab_result,
    from_staircase_result,
)
from struct_draw.core.data import (
    BeamData,
    ColumnData,
    FootingData,
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


def test_from_footing_result() -> None:
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
    result = from_footing_result(design)
    assert isinstance(result, FootingData)
    assert result.name == "F2"
    assert result.length_in == 72.0
    assert result.width_in == 72.0
    assert result.mid_thickness_in == 18.0


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
