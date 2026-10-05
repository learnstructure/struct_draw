"""Example 4 — Build a footing drawing from an ACI 318 design & detailing result.

This example demonstrates how to consume results from an external calculation library
(such as `aci318`) via `struct_draw.adapters.aci318.from_footing_result`.

Workflow:
  1. Receive or construct an ACI 318 Footing Design + Detailing result object.
  2. Translate it into a :class:`struct_draw.core.data.FootingData` using
     :func:`struct_draw.adapters.aci318.from_footing_result`.
  3. Render to DXF using :func:`struct_draw.save_dxf`.
"""

from __future__ import annotations

from pathlib import Path

# Add project root to sys.path for direct execution without pip install
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from types import SimpleNamespace

import struct_draw as sd
from struct_draw.adapters.aci318 import from_footing_result


def make_fake_aci318_footing_result() -> tuple[SimpleNamespace, SimpleNamespace]:
    """Construct a mock ACI 318 footing design and detailing result."""
    design = SimpleNamespace(
        name="F3",
        length=80.0,             # 80 inches (6.67 ft)
        width=80.0,              # 80 inches
        mid_thickness=20.0,      # 20 inches
        edge_thickness=10.0,     # 10 inches
        column_width=16.0,       # 16 inches
        column_depth=16.0,       # 16 inches
        column_height=90.0,      # 90 inches
        footing_depth=60.0,      # 60 inches below GL
        plinth_height=24.0,      # 24 inches above GL
        cover=3.0,               # 3 inches
        bar_dia=0.75,            # #6 bar (0.75 in)
        bar_spacing=6.0,         # 6 inches c/c
        Ld=30.0,                 # Development length 30 inches
    )

    detailing = SimpleNamespace(
        column_bars=(
            SimpleNamespace(mark="CB1", size="#8", quantity=4, length=120.0),
        ),
        column_stirrup=SimpleNamespace(size="#4", spacing=6.0, legs=2),
        schedule_rows=(
            SimpleNamespace(mark="F3-B1", size="#6", quantity=14, length=86.0, remarks="Bottom X-Dir"),
            SimpleNamespace(mark="F3-B2", size="#6", quantity=14, length=86.0, remarks="Bottom Y-Dir"),
            SimpleNamespace(mark="F3-CB1", size="#8", quantity=4, length=120.0, remarks="Column Starter Dowels"),
            SimpleNamespace(mark="F3-T1", size="#4", quantity=15, length=56.0, remarks="Column Ties @ 6\" c/c"),
        ),
    )

    return design, detailing


def main() -> None:
    design, detailing = make_fake_aci318_footing_result()

    # Convert calculation results into struct_draw FootingData
    footing_data = from_footing_result((design, detailing))

    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / "output_footing_from_aci318.dxf"
    sd.save_dxf(footing_data, out_path)

    print(f"Successfully generated footing drawing from ACI 318 result: {out_path.resolve()}")
    print(f"  Footing Name: {footing_data.name}")
    print(f"  Dimensions: {footing_data.length_in}\" x {footing_data.width_in}\" x {footing_data.mid_thickness_in}\"")


if __name__ == "__main__":
    main()
