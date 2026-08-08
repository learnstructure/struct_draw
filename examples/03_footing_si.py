"""Example 3b — Render a spread footing drawing (Plan + Section) in SI metric units.

This example demonstrates generating a structural footing drawing using
SI metric unit parameters (mm) via :meth:`struct_draw.core.data.FootingData.from_metric`.
"""

from __future__ import annotations

from pathlib import Path
import sys

# Add project root to sys.path for direct script execution without pip install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import struct_draw as sd
from struct_draw.core.data import FootingData, Rebar, Stirrup


def main() -> None:
    # SI Units creation using FootingData.from_metric (parameters in mm)
    footing_si = FootingData.from_metric(
        name="F2",
        length_mm=1600.0,           # Footing length (1600 mm)
        width_mm=1600.0,            # Footing width (1600 mm)
        mid_thick_mm=400.0,         # Central thickness (400 mm)
        edge_thick_mm=200.0,        # Edge thickness (200 mm)
        col_width_mm=350.0,         # Column width (350 mm)
        col_depth_mm=350.0,         # Column depth (350 mm)
        col_height_mm=2100.0,       # Column height (2100 mm)
        fd_depth_mm=1500.0,         # Foundation depth below GL (1500 mm)
        pl_height_mm=600.0,         # Plinth level height above GL (600 mm)
        cover_mm=75.0,              # Concrete clear cover (75 mm)
        bar_dia_mm=12.0,            # Rebar diameter (12 mm)
        bar_spacing_mm=150.0,       # Rebar spacing c/c (150 mm)
        ld_mm=600.0,                # Development length Ld (600 mm)
        column_bars=(
            Rebar(mark="C1", size="16φ", quantity=4, length_in=3000.0),
        ),
        column_stirrups=Stirrup(size="8φ", spacing_in=100.0, legs=2),
    )

    out_path = Path("output_footing_si.dxf")
    sd.save_dxf(footing_si, out_path)
    print(f"Saved SI footing drawing to: {out_path.resolve()}")


if __name__ == "__main__":
    main()
