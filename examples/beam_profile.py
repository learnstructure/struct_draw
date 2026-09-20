"""Example 6 — Continuous Multi-Span Beam Profile Drawing (L-Section & Cross-Sections).

This example demonstrates generating a complete multi-span continuous beam drawing sheet
(Longitudinal Section / Profile + Companion Support/Mid-Span Cross-Sections)
using SI metric parameters via :meth:`struct_draw.core.data.BeamProfileData.from_metric`.
"""

from __future__ import annotations

from pathlib import Path
import sys

# Add project root to sys.path for direct script execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import struct_draw as sd
from struct_draw.core.data import BeamProfileData, Rebar, Stirrup


def main() -> None:
    # 1. Define a 5-span continuous beam profile in SI Metric units (mm)
    beam_profile = BeamProfileData.from_metric(
        name="L-SECTION OF BEAM ALONG GRIDS A-A",
        grid_line_name="A-A",
        spans=(5500.0, 4000.0, 3000.0, 4000.0, 5500.0),  # Span lengths
        col_width=450.0,                               # Column width at supports
        beam_width=450.0,                              # Beam cross-section width
        beam_depth=450.0,                              # Beam cross-section depth
        cover=40.0,                                    # Clear concrete cover
        col_extension=975.0,                           # Vertical column stub extension
        grid_extension=1500.0,                         # Grid line bubble extension
        grid_labels=("A", "B", "C", "D", "E", "F"),       # Grid line labels
        level_text="PL+3.0 m",                            # Plinth / floor level label
        support_stirrup_spacing=100.0,                 # Dense stirrup spacing at supports
        mid_stirrup_spacing=150.0,                     # Mid-span stirrup spacing
        stirrup=Stirrup(size="10mm dia", spacing_in=100.0, legs=2),
        top_bars=(Rebar(mark="TB1", size="20mm dia", quantity=2),),
        bottom_bars=(Rebar(mark="BB1", size="20mm dia", quantity=3),),
        top_extra_bars=(Rebar(mark="EB1", size="16mm dia", quantity=2),),
    )

    # 2. Export directly to DXF using struct_draw.save_dxf
    out_dir = Path(__file__).resolve().parent
    out_path = out_dir / "output" / "output_beam_profile.dxf"
    sd.save_dxf(beam_profile, out_path)
    print(f"Successfully generated continuous beam profile DXF: {out_path.resolve()}")


if __name__ == "__main__":
    main()
