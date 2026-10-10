"""Example 4 — Build an isolated spread footing drawing from actual ACI 318 design.

Workflow:
  1. Perform actual ACI 318-19 isolated spread footing structural design using `aci318`.
  2. Translate the calculation & reinforcement detailing output into a `struct_draw.IsolatedFootingData`
     schema using `struct_draw.adapters.aci318.from_isolated_footing_result`.
  3. Render professional construction DXF drawing using `struct_draw.save_dxf`.
"""

from __future__ import annotations

from pathlib import Path
import sys

# Ensure projects in workspace are discoverable when run directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aci318 import (
    ACI318_19,
    Concrete,
    IsolatedFooting,
    LoadEffects,
    Steel,
)
import struct_draw as sd
from struct_draw.adapters.aci318 import from_isolated_footing_result


def design_isolated_footing():
    """Run an actual ACI 318-19 design for an isolated spread footing."""
    code = ACI318_19()
    concrete = Concrete(fc=3.0)  # f'c = 3.0 ksi
    steel = Steel(fy=60.0)      # fy = 60.0 ksi

    # Factored column demand: Pu = 272 kips, Mu = 150 kip-in
    loads = LoadEffects(Pu=272.0, Mu=150.0)

    # Footing dimensions: 8.0 ft x 8.0 ft x 24.0 in thick supporting 16" x 16" column
    footing = IsolatedFooting(
        length=8.0,            # 8.0 ft (96 in)
        width=8.0,             # 8.0 ft (96 in)
        thickness=24.0,        # 24.0 in
        col_c1=16.0,           # 16.0 in column
        col_c2=16.0,           # 16.0 in column
        concrete=concrete,
        steel=steel,
        code=code,
        allowable_q=5.0,       # 5.0 ksf
        bar_size="#6",
        member_id="FTG-101",
    )

    result = footing.design(loads=loads)
    return footing, result


def main() -> None:
    footing, result = design_isolated_footing()

    print("=" * 60)
    print(" 1. ACI 318-19 ISOLATED FOOTING DESIGN OUTPUT")
    print("=" * 60)
    print(f"Footing ID:           {footing.member_id}")
    print(f"Dimensions:           {footing.length:.1f} ft x {footing.width:.1f} ft x {footing.thickness:.1f} in")
    print(f"Column:               {footing.col_c1:.0f}\" x {footing.col_c2:.0f}\"")
    print(f"Status:               {result.status}")
    print(f"Soil Pressure:        {result.max_bearing_pressure:.2f} ksf (allowable: {result.allowable_bearing_capacity:.2f} ksf)")
    print(f"One-Way Shear:        {result.one_way_shear.status} (DCR = {result.one_way_shear.demand_capacity_ratio:.2f})")
    print(f"Punching Shear:       {result.punching_shear.status} (DCR = {result.punching_shear.demand_capacity_ratio:.2f})")
    print(f"Required As (X / Y):  {result.required_As_x:.2f} in^2 / {result.required_As_y:.2f} in^2")
    print("-" * 60)

    # Convert calculation results into struct_draw FootingData
    footing_data = from_isolated_footing_result((footing, result))

    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / "output_footing_from_aci318.dxf"
    sd.save_dxf(footing_data, out_path)

    print(" 2. STRUCT_DRAW CAD GENERATION")
    print("-" * 60)
    print(f"Successfully generated footing drawing from ACI 318 result: {out_path.resolve()}")
    print(f"  Footing Name:       {footing_data.name}")
    print(f"  Drawing Dimensions: {footing_data.length_in:.1f}\" x {footing_data.width_in:.1f}\" x {footing_data.mid_thickness_in:.1f}\"")
    print(f"  Bar Diameter:       {footing_data.bar_dia_in:.3f}\" (#{int(round(footing_data.bar_dia_in * 8))})")
    print(f"  Bar Spacing:        {footing_data.bar_spacing_in:.1f}\" c/c")
    print("=" * 60)


if __name__ == "__main__":
    main()
