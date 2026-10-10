"""Example 3a — Render an isolated spread footing drawing (Plan + Section) in Imperial units.

This example demonstrates generating a structural footing drawing using
Imperial unit parameters (inches) directly via :class:`struct_draw.core.data.IsolatedFootingData`.
"""

from __future__ import annotations

from pathlib import Path
import sys

# Add project root to sys.path for direct script execution without pip install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import struct_draw as sd
from struct_draw.core.data import IsolatedFootingData, Rebar, ScheduleRow, Stirrup


def main() -> None:
    # IsolatedFootingData creation using IsolatedFootingData.from_imperial (parameters in inches)
    footing_imperial = IsolatedFootingData.from_imperial(
        name="F1",
        length=72.0,             # Footing length (6 ft = 72 in)
        width=72.0,              # Footing width (6 ft = 72 in)
        mid_thick=18.0,          # Central thickness (18 in)
        edge_thick=10.0,         # Sloped edge thickness (10 in)
        col_width=16.0,          # Column width (16 in)
        col_depth=16.0,          # Column depth (16 in)
        col_height=96.0,         # Column stem height (8 ft = 96 in)
        fd_depth=60.0,           # Depth of foundation below GL (5 ft = 60 in)
        pl_height=24.0,          # Plinth height above GL (2 ft = 24 in)
        cover=3.0,               # Clear cover to footing steel (3 in)
        bar_dia=0.625,           # #5 rebar (5/8 in)
        bar_spacing=6.0,         # 6 in c/c spacing bothways
        ld=24.0,                 # Development length Ld into footing (24 in)
        column_bars=(
            Rebar(mark="CB1", size="#7", quantity=4, length_in=120.0),
        ),
        column_stirrups=Stirrup(size="#3", spacing_in=6.0, legs=2),
        schedule=(
            ScheduleRow(mark="F1-B1", size="#5", quantity=12, length_in=78.0, remarks="Bottom X-Dir"),
            ScheduleRow(mark="F1-B2", size="#5", quantity=12, length_in=78.0, remarks="Bottom Y-Dir"),
            ScheduleRow(mark="F1-CB1", size="#7", quantity=4, length_in=120.0, remarks="Column Dowels"),
            ScheduleRow(mark="F1-T1", size="#3", quantity=20, length_in=60.0, remarks="Column Ties @ 6\" c/c"),
        ),
    )

    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / "output_footing_imperial.dxf"
    sd.save_dxf(footing_imperial, out_path)
    print(f"Saved Imperial footing drawing to: {out_path.resolve()}")


if __name__ == "__main__":
    main()
