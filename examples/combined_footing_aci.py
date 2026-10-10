"""Example 5 — Build a two-column combined footing drawing from actual ACI 318 design.

Workflow:
  1. Perform actual ACI 318-19 combined footing structural design using `aci318`.
  2. Translate the calculation & detailing output into a `struct_draw.CombinedFootingData`
     schema using `struct_draw.adapters.aci318.from_combined_footing_result`.
  3. Render professional construction DXF drawing using `struct_draw.save_dxf`.
"""

from __future__ import annotations

from pathlib import Path
import sys

# Ensure projects in workspace are discoverable when run directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aci318 import (
    ACI318_19,
    CombinedFooting,
    Concrete,
    Steel,
)
import struct_draw as sd
from struct_draw.adapters.aci318 import from_combined_footing_result


def design_combined_footing():
    """Run an actual ACI 318-19 design for a two-column combined rectangular footing."""
    code = ACI318_19()
    concrete = Concrete(fc=4.0)  # f'c = 4.0 ksi
    steel = Steel(fy=60.0)      # fy = 60.0 ksi

    # Combined footing supporting two columns:
    # Column spacing: 12.0 ft, Col 1: 16"x16", Col 2: 18"x18"
    footing = CombinedFooting(
        column_spacing_ft=12.0,
        col1_c1=16.0,
        col1_c2=16.0,
        col2_c1=18.0,
        col2_c2=18.0,
        concrete=concrete,
        steel=steel,
        code=code,
        allowable_q=5.0,        # 5.0 ksf
        cantilever_col1_ft=2.0, # 2.0 ft projection on Col 1 side
        thickness=26.0,         # 26.0 in
        cover=3.0,              # 3.0 in
        bar_size="#8",
        member_id="CFTG-201",
    )

    # Column loads: P1 = 180 kips, P2 = 250 kips
    result = footing.design(p1_kip=180.0, p2_kip=250.0)
    return footing, result


def main() -> None:
    footing, result = design_combined_footing()

    print("=" * 60)
    print(" 1. ACI 318-19 COMBINED FOOTING DESIGN OUTPUT")
    print("=" * 60)
    print(f"Footing ID:           {footing.member_id}")
    print(f"Dimensions:           {result.length:.1f} ft x {result.width:.1f} ft x {result.thickness:.1f} in")
    print(f"Column Spacing:       {footing.column_spacing_ft:.1f} ft (Col 1: {footing.col1_c1:.0f}\"x{footing.col1_c2:.0f}\", Col 2: {footing.col2_c1:.0f}\"x{footing.col2_c2:.0f}\")")
    print(f"Status:               {result.status}")
    print(f"Soil Pressure:        {result.soil_pressure:.2f} ksf (allowable: {result.allowable_pressure:.2f} ksf)")
    print(f"Top Steel Bars:       {result.top_steel_bars}")
    print(f"Bottom Steel Bars:    {result.bottom_steel_bars}")
    print(f"One-Way Shear:        {result.one_way_shear.status} (DCR = {result.one_way_shear.demand_capacity_ratio:.2f})")
    print(f"Col 1 Punching:       {result.punching_shear_col1.status} (DCR = {result.punching_shear_col1.demand_capacity_ratio:.2f})")
    print(f"Col 2 Punching:       {result.punching_shear_col2.status} (DCR = {result.punching_shear_col2.demand_capacity_ratio:.2f})")
    print("-" * 60)

    # Convert calculation results into struct_draw CombinedFootingData
    cf_data = from_combined_footing_result((footing, result))

    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / "output_combined_footing_from_aci318.dxf"
    sd.save_dxf(cf_data, out_path)

    print(" 2. STRUCT_DRAW CAD GENERATION")
    print("-" * 60)
    print(f"Successfully generated combined footing drawing: {out_path.resolve()}")
    print(f"  Footing Name:       {cf_data.name}")
    print(f"  Pad Dimensions:     {cf_data.total_length_in:.1f}\" L x {cf_data.width_in:.1f}\" W x {cf_data.thickness_in:.1f}\" T")
    print(f"  Col Spacing:        {cf_data.col_spacing_in:.1f}\"")
    print(f"  Projections:        Left {cf_data.proj_left_in:.1f}\", Right {cf_data.proj_right_in:.1f}\"")
    print(f"  Bottom Bar:         Dia = {cf_data.bar_dia_in:.3f}\", Spacing = {cf_data.bar_spacing_in:.1f}\"")
    if cf_data.top_bar_dia_in is not None:
        print(f"  Top Bar:            Dia = {cf_data.top_bar_dia_in:.3f}\", Spacing = {cf_data.top_bar_spacing_in:.1f}\"")
    print("=" * 60)


if __name__ == "__main__":
    main()
