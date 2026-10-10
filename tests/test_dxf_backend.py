"""Backend tests for the v2 DXF writer.

These tests gate ``ezdxf`` behind a ``pytest.importorskip`` so
they are skipped automatically when the optional dependency is
not installed in the active environment.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ezdxf = pytest.importorskip("ezdxf")

from struct_draw.backends import save_dxf  # noqa: E402
from struct_draw.core.data import (  # noqa: E402
    BeamData,
    ColumnData,
    CombinedFootingData,
    IsolatedFootingData,
    FootingData,
    GeometrySection,
    ScheduleRow,
    ScheduleTableData,
    SlabData,
    StaircaseData,
)


# ---------------------------------------------------------------------------
# Tiny dataclass payloads
# ---------------------------------------------------------------------------


def _beam() -> BeamData:
    return BeamData(
        name="B1",
        section=GeometrySection(width_in=12.0, depth_in=24.0, cover_in=1.5),
        length_in=240.0,
    )


def _column() -> ColumnData:
    return ColumnData(
        name="C1",
        section=GeometrySection(width_in=18.0, depth_in=18.0, cover_in=1.5),
        height_in=120.0,
    )


def _column_with_schedule() -> ColumnData:
    return ColumnData(
        name="C2",
        section=GeometrySection(width_in=18.0, depth_in=18.0, cover_in=1.5),
        height_in=120.0,
        schedule=(
            ScheduleRow(mark="C2-1", size="#8", quantity=4, length_in=144.0, remarks="Straight"),
        ),
    )


def _footing() -> IsolatedFootingData:
    return IsolatedFootingData(
        name="F1",
        length_in=96.0,
        width_in=96.0,
    )


def _footing_with_schedule() -> FootingData:
    return FootingData(
        name="F1",
        length_in=96.0,
        width_in=96.0,
        schedule=(
            ScheduleRow(mark="F1-1", size="#6", quantity=16, length_in=90.0, remarks="Straight"),
        ),
    )


def _combined_footing_imperial() -> CombinedFootingData:
    return CombinedFootingData.from_imperial(
        name="CF1",
        proj_left=60.0,
        proj_right=48.0,
        col_spacing=36.0,
    )


def _combined_footing_si() -> CombinedFootingData:
    return CombinedFootingData.from_metric(
        name="CF2",
        proj_left=1500.0,
        proj_right=1200.0,
        col_spacing=800.0,
    )


def _combined_footing_with_schedule() -> CombinedFootingData:
    return CombinedFootingData.from_metric(
        name="CF3",
        proj_left=1500.0,
        proj_right=1200.0,
        col_spacing=800.0,
        schedule=(
            ScheduleRow(mark="CF3-1", size="16φ", quantity=8, length_in=3800.0, remarks="Bottom Long."),
        ),
    )


def _slab() -> SlabData:
    return SlabData(name="S1", width_in=120.0, length_in=240.0, thickness_in=8.0)


def _stair() -> StaircaseData:
    return StaircaseData(
        name="ST1",
        flight_width_in=48.0,
        flight_length_in=120.0,
    )


def _schedule_table() -> ScheduleTableData:
    return ScheduleTableData(
        title="SCHEDULE TEST",
        rows=[
            ScheduleRow(mark="T1", size="#5", quantity=10, length_in=120.0, remarks="Straight"),
        ],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "data",
    [
        _beam(),
        _column(),
        _column_with_schedule(),
        _footing(),
        _footing_with_schedule(),
        _combined_footing_imperial(),
        _combined_footing_si(),
        _combined_footing_with_schedule(),
        _slab(),
        _stair(),
        _schedule_table(),
    ],
    ids=[
        "beam",
        "column",
        "column_with_schedule",
        "footing",
        "footing_with_schedule",
        "combined_footing_imperial",
        "combined_footing_si",
        "combined_footing_with_schedule",
        "slab",
        "stair",
        "schedule_table",
    ],
)
def test_save_dxf_writes_valid_file(tmp_path: Path, data) -> None:
    out_path = tmp_path / "out.dxf"
    saved = save_dxf(data, out_path)
    assert saved == out_path
    assert out_path.exists()
    assert out_path.stat().st_size > 0

    doc = ezdxf.readfile(str(out_path))
    assert doc is not None
    msp = doc.modelspace()
    assert len(msp) > 0


def test_footing_and_cf_schedule_rendering() -> None:
    from struct_draw.backends import render

    res_f = render(_footing_with_schedule())
    assert "schedule" in res_f.metadata.get("views", [])
    assert "plan" in res_f.metadata.get("views", [])
    assert "section" in res_f.metadata.get("views", [])

    res_cf = render(_combined_footing_with_schedule())
    assert "schedule" in res_cf.metadata.get("views", [])
    assert "plan" in res_cf.metadata.get("views", [])
    assert "section" in res_cf.metadata.get("views", [])


def test_save_dxf_creates_required_layers(tmp_path: Path) -> None:
    out_path = tmp_path / "beam.dxf"
    save_dxf(_beam(), out_path)

    doc = ezdxf.readfile(str(out_path))
    layer_names = {l.dxf.name for l in doc.layers}
    for required in ("REBAR", "CONC_OUTLINE", "DIM_LINEAR"):
        assert required in layer_names