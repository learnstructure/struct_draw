"""Example 5 — Render a staircase drawing (Section + Plan) in SI metric units.

This example demonstrates generating a complete structural staircase drawing
(waist slab elevation section + 2-flight plan view) using :meth:`struct_draw.core.data.StaircaseData.from_metric`.
"""

from __future__ import annotations

from pathlib import Path
import sys

# Add project root to sys.path for direct script execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import struct_draw as sd
from struct_draw.core.data import StaircaseData


def main() -> None:
    # Construct a RCC staircase flight using SI metric units (dimensions in mm)
    stair_si = StaircaseData.from_metric(
        name="ST1",
        flight_width=1200.0,       # Flight width (1200 mm)
        riser=150.0,               # Riser height (150 mm)
        tread=300.0,               # Tread depth (300 mm)
        num_risers=12,                # Number of risers
        waist=190.0,               # Waist slab thickness (190 mm)
        cover=30.0,                # Clear cover (30 mm)
        bottom_landing=1915.0,     # Distance from Grid 1 to 1st riser (1915 mm)
        top_landing=285.0,         # Distance from last riser to Grid 2 (285 mm)
        beam_left_w=230.0,         # Left beam width (230 mm)
        beam_left_h=350.0,         # Left beam depth (350 mm)
        beam_right_w=350.0,        # Right beam width (350 mm)
        beam_right_h=550.0,        # Right beam depth (550 mm)
        main_bar_dia=12.0,         # Main rebar diameter (12 mm)
        main_bar_spacing=125.0,    # Main rebar spacing (125 mm c/c)
        dist_bar_dia=10.0,         # Distribution bar diameter (10 mm)
        dist_bar_spacing=150.0,    # Distribution bar spacing (150 mm c/c)
        nosing_bar_dia=8.0,        # Nosing rebar diameter (8 mm)
    )

    out_path = Path("output_staircase_si.dxf")
    sd.save_dxf(stair_si, out_path)
    print(f"Saved SI staircase drawing to: {out_path.resolve()}")


if __name__ == "__main__":
    main()
