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
    FootingData,
    GeometrySection,
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


def _footing() -> FootingData:
    return FootingData(
        name="F1",
        length_in=96.0,
        width_in=96.0,
    )


def _combined_footing_imperial() -> CombinedFootingData:
    return CombinedFootingData(
        name="CF1",
        proj_left_in=60.0,
        proj_right_in=48.0,
        col_spacing_in=36.0,
    )


def _combined_footing_si() -> CombinedFootingData:
    return CombinedFootingData.from_metric(
        name="CF2",
        proj_left_mm=1500.0,
        proj_right_mm=1200.0,
        col_spacing_mm=800.0,
    )


def _slab() -> SlabData:
    return SlabData(name="S1", width_in=120.0, length_in=240.0, thickness_in=8.0)


def _stair() -> StaircaseData:
    return StaircaseData(
        name="ST1",
        flight_width_in=48.0,
        flight_length_in=120.0,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "data",
    [
        _beam(),
        _column(),
        _footing(),
        _combined_footing_imperial(),
        _combined_footing_si(),
        _slab(),
        _stair(),
    ],
    ids=[
        "beam",
        "column",
        "footing",
        "combined_footing_imperial",
        "combined_footing_si",
        "slab",
        "stair",
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


def test_save_dxf_creates_required_layers(tmp_path: Path) -> None:
    out_path = tmp_path / "beam.dxf"
    save_dxf(_beam(), out_path)

    doc = ezdxf.readfile(str(out_path))
    layer_names = {l.dxf.name for l in doc.layers}
    for required in ("REBAR", "CONC_OUTLINE", "DIM_LINEAR"):
        assert required in layer_names