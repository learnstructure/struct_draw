"""Example 3a — Render a spread footing drawing (Plan + Section) in Imperial units.

This example demonstrates generating a structural footing drawing using
Imperial unit parameters (inches) directly via :class:`struct_draw.core.data.FootingData`.
"""

from __future__ import annotations

from pathlib import Path
import sys

# Add project root to sys.path for direct script execution without pip install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import struct_draw as sd
from struct_draw.core.data import FootingData, Rebar, Stirrup


def main() -> None:
    # Direct FootingData creation (Imperial units in inches)
    footing_imperial = FootingData(
        name="F1",
        length_in=72.0,             # Footing length (6 ft = 72 in)
        width_in=72.0,              # Footing width (6 ft = 72 in)
        mid_thickness_in=18.0,      # Central thickness (18 in)
        edge_thickness_in=10.0,     # Sloped edge thickness (10 in)
        column_width_in=16.0,       # Column width (16 in)
        column_depth_in=16.0,       # Column depth (16 in)
        column_height_in=96.0,      # Column stem height (8 ft = 96 in)
        footing_depth_in=60.0,      # Depth of foundation below GL (5 ft = 60 in)
        plinth_height_in=24.0,      # Plinth height above GL (2 ft = 24 in)
        cover_in=3.0,               # Clear cover to footing steel (3 in)
        bar_dia_in=0.625,           # #5 rebar (5/8 in)
        bar_spacing_in=6.0,         # 6 in c/c spacing bothways
        column_bars=(
            Rebar(mark="CB1", size="#7", quantity=4, length_in=120.0),
        ),
        column_stirrups=Stirrup(size="#3", spacing_in=6.0, legs=2),
        development_length_in=24.0, # Development length Ld into footing (24 in)
    )

    out_path = Path("output_footing_imperial.dxf")
    sd.save_dxf(footing_imperial, out_path)
    print(f"Saved Imperial footing drawing to: {out_path.resolve()}")


if __name__ == "__main__":
    main()
