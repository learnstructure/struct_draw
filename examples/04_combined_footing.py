"""Example 4 — Render a combined footing drawing (Plan + Section) in SI and Imperial units.

This example demonstrates generating production-ready combined footing drawings
using :class:`struct_draw.core.data.CombinedFootingData`.
"""

from __future__ import annotations

from pathlib import Path
import sys

# Add project root to sys.path for direct script execution without pip install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import struct_draw as sd
from struct_draw.core.data import CombinedFootingData, Rebar, Stirrup


def main() -> None:
    # 1. SI Metric Combined Footing Example
    cf_si = CombinedFootingData.from_metric(
        name="CF1",
        proj_left_mm=1500.0,
        proj_right_mm=1200.0,
        col_spacing_mm=800.0,
        width_mm=1600.0,
        thickness_mm=400.0,
        col1_width_mm=350.0,
        col1_depth_mm=350.0,
        col2_width_mm=350.0,
        col2_depth_mm=350.0,
        fd_depth_mm=1500.0,
        pl_height_mm=600.0,
        pcc_thick_mm=75.0,
        soling_thick_mm=75.0,
        cover_mm=50.0,
        bar_dia_mm=12.0,
        bar_spacing_mm=150.0,
        top_bar_dia_mm=12.0,
        top_bar_spacing_mm=150.0,
        plinth_beam_w_mm=230.0,
        plinth_beam_h_mm=350.0,
        found_beam_w_mm=230.0,
        found_beam_h_mm=300.0,
        ld_mm=600.0,
        column_bars=(
            Rebar(mark="C1", size="16φ", quantity=4, length_in=3000.0),
        ),
        column_stirrups=Stirrup(size="8φ", spacing_in=100.0, legs=2),
    )

    si_out_path = Path("output_combined_footing_si.dxf")
    sd.save_dxf(cf_si, si_out_path)
    print(f"Saved SI combined footing drawing to: {si_out_path.resolve()}")

    # 2. Imperial Combined Footing Example
    cf_imperial = CombinedFootingData(
        name="CF2",
        proj_left_in=60.0,
        proj_right_in=48.0,
        col_spacing_in=36.0,
        width_in=64.0,
        thickness_in=16.0,
        col1_width_in=14.0,
        col1_depth_in=14.0,
        col2_width_in=14.0,
        col2_depth_in=14.0,
        footing_depth_in=60.0,
        plinth_height_in=24.0,
        pcc_thickness_in=3.0,
        soling_thickness_in=3.0,
        cover_in=2.0,
        bar_dia_in=0.5,
        bar_spacing_in=6.0,
        top_bar_dia_in=0.5,
        top_bar_spacing_in=6.0,
        plinth_beam_width_in=9.0,
        plinth_beam_depth_in=14.0,
        foundation_beam_width_in=9.0,
        foundation_beam_depth_in=12.0,
        development_length_in=24.0,
        column_bars=(
            Rebar(mark="CB1", size="#7", quantity=4, length_in=120.0),
        ),
        column_stirrups=Stirrup(size="#3", spacing_in=6.0, legs=2),
    )

    imp_out_path = Path("output_combined_footing_imperial.dxf")
    sd.save_dxf(cf_imperial, imp_out_path)
    print(f"Saved Imperial combined footing drawing to: {imp_out_path.resolve()}")


if __name__ == "__main__":
    main()
