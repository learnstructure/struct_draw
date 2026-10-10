"""Example 3b — Render an isolated spread footing drawing (Plan + Section) in SI metric units.

This example demonstrates generating a structural footing drawing using
SI metric unit parameters (mm) via :meth:`struct_draw.core.data.IsolatedFootingData.from_metric`.
"""

from __future__ import annotations

from pathlib import Path
import sys

# Add project root to sys.path for direct script execution without pip install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import struct_draw as sd
from struct_draw.core.data import IsolatedFootingData, Rebar, ScheduleRow, Stirrup


def main() -> None:
    # SI Units creation using IsolatedFootingData.from_metric (parameters in mm)
    footing_si = IsolatedFootingData.from_metric(
        name="F2",
        length=1600.0,           # Footing length (1600 mm)
        width=1600.0,            # Footing width (1600 mm)
        mid_thick=400.0,         # Central thickness (400 mm)
        edge_thick=200.0,        # Edge thickness (200 mm)
        col_width=350.0,         # Column width (350 mm)
        col_depth=350.0,         # Column depth (350 mm)
        col_height=2100.0,       # Column height (2100 mm)
        fd_depth=1500.0,         # Foundation depth below GL (1500 mm)
        pl_height=600.0,         # Plinth level height above GL (600 mm)
        cover=75.0,              # Concrete clear cover (75 mm)
        bar_dia=12.0,            # Rebar diameter (12 mm)
        bar_spacing=150.0,       # Rebar spacing c/c (150 mm)
        ld=600.0,                # Development length Ld (600 mm)
        column_bars=(
            Rebar(mark="C1", size="16φ", quantity=4, length_in=3000.0),
        ),
        column_stirrups=Stirrup(size="8φ", spacing_in=100.0, legs=2),
        schedule=(
            ScheduleRow(mark="F2-1", size="12φ", quantity=11, length_in=1650.0, remarks="Bottom mesh X-dir"),
            ScheduleRow(mark="F2-2", size="12φ", quantity=11, length_in=1650.0, remarks="Bottom mesh Y-dir"),
            ScheduleRow(mark="F2-C1", size="16φ", quantity=4, length_in=3000.0, remarks="Column starter dowels"),
            ScheduleRow(mark="F2-T1", size="8φ", quantity=21, length_in=1280.0, remarks="Column ties @ 100mm c/c"),
        ),
        scale=sd.SCALE_1_25,     # 1:25 scale for footing detailing
        unit=sd.DrawingUnit.MM,  # Target modelspace units in millimeters
    )

    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / "output_footing_si.dxf"
    sd.save_dxf(footing_si, out_path)
    print(f"Saved SI footing drawing to: {out_path.resolve()} (scale: {footing_si.scale.name}, unit: {footing_si.unit.name})")


if __name__ == "__main__":
    main()
