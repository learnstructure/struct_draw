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
        proj_left=1500.0,
        proj_right=1200.0,
        col_spacing=800.0,
        width=1600.0,
        thickness=400.0,
        col1_width=350.0,
        col1_depth=350.0,
        col2_width=350.0,
        col2_depth=350.0,
        fd_depth=1500.0,
        pl_height=600.0,
        pcc_thick=75.0,
        soling_thick=75.0,
        cover=50.0,
        bar_dia=12.0,
        bar_spacing=150.0,
        top_bar_dia=12.0,
        top_bar_spacing=150.0,
        plinth_beam_w=230.0,
        plinth_beam_h=350.0,
        found_beam_w=230.0,
        found_beam_h=300.0,
        ld=600.0,
        column_bars=(
            Rebar(mark="C1", size="16φ", quantity=4, length_in=3000.0),
        ),
        column_stirrups=Stirrup(size="8φ", spacing_in=100.0, legs=2),
    )

    si_out_path = Path("output_combined_footing_si.dxf")
    sd.save_dxf(cf_si, si_out_path)
    print(f"Saved SI combined footing drawing to: {si_out_path.resolve()}")

    # 2. Imperial Combined Footing Example
    cf_imperial = CombinedFootingData.from_imperial(
        name="CF2",
        proj_left=60.0,
        proj_right=48.0,
        col_spacing=36.0,
        width=64.0,
        thickness=16.0,
        col1_width=14.0,
        col1_depth=14.0,
        col2_width=14.0,
        col2_depth=14.0,
        fd_depth=60.0,
        pl_height=24.0,
        pcc_thick=3.0,
        soling_thick=3.0,
        cover=2.0,
        bar_dia=0.5,
        bar_spacing=6.0,
        top_bar_dia=0.5,
        top_bar_spacing=6.0,
        plinth_beam_w=9.0,
        plinth_beam_h=14.0,
        found_beam_w=9.0,
        found_beam_h=12.0,
        ld=24.0,
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
