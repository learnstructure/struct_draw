"""Example 7 — Render a column drawing (Section + Elevation) using struct_draw.elements.column.

This example demonstrates constructing a column structural drawing using
:class:`struct_draw.core.data.ColumnData` and rendering both the cross-section
view and longitudinal elevation view using the element functions in
:mod:`struct_draw.elements.column`.
"""

from __future__ import annotations

from pathlib import Path
import sys

# Add project root to sys.path for direct script execution without pip install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import struct_draw as sd
from struct_draw.core.data import ColumnData, GeometrySection, Rebar, ScheduleRow, Stirrup
from struct_draw.elements import column as column_element


def main() -> None:
    # 1. Define ColumnData with geometry, longitudinal bars, and stirrups
    # Column C1: 18" x 18" section, 120" (10 ft) clear height, 1.5" cover
    column = ColumnData(
        name="C1",
        section=GeometrySection(
            width_in=18.0,   # 18 inches
            depth_in=18.0,   # 18 inches
            cover_in=1.5,    # 1.5 inches clear cover
        ),
        height_in=120.0,     # 120 inches (10 ft height)
        longitudinal_bars=(
            Rebar(mark="C1", size="#8", quantity=1, length_in=120.0, remarks="Corner 1"),
            Rebar(mark="C2", size="#8", quantity=1, length_in=120.0, remarks="Corner 2"),
            Rebar(mark="C3", size="#8", quantity=1, length_in=120.0, remarks="Corner 3"),
            Rebar(mark="C4", size="#8", quantity=1, length_in=120.0, remarks="Corner 4"),
        ),
        stirrups=Stirrup(
            size="#3",        # #3 tie / stirrup
            spacing_in=6.0,   # 6 in c/c spacing
            legs=2,
        ),
        schedule=(
            ScheduleRow(mark="C1-C4", size="#8", quantity=4, length_in=120.0, remarks="4-#8 Longitudinal"),
            ScheduleRow(mark="T1", size="#3", quantity=20, length_in=66.0, remarks="#3 Ties @ 6\" c/c"),
        ),
    )

    print(f"Created ColumnData for {column.name}: {column.section.width_in}x{column.section.depth_in} in, height={column.height_in} in")
    print(f"Longitudinal bars count: {len(column.longitudinal_bars)}, Stirrup: {column.stirrups.size} @ {column.stirrups.spacing_in}\"")

    # 2. Render using high-level struct_draw.save_dxf or struct_draw.render
    out_path = Path("output_column.dxf")
    try:
        sd.save_dxf(column, out_path)
        print(f"Successfully saved column drawing to: {out_path.resolve()}")
    except Exception as err:
        print(f"Note on DXF saving (ezdxf dependency check): {err}")

    # # 3. Direct element functions usage demonstration with mock target
    # class Target:
    #     def add_line(self, *args, **kwargs): pass
    #     def add_lwpolyline(self, *args, **kwargs): pass
    #     def add_text(self, *args, **kwargs): pass
    #     def add_circle(self, *args, **kwargs): pass
    #     def add_linear_dim(self, *args, **kwargs): return self
    #     def set_text(self, *args, **kwargs): pass
    #     def render(self, *args, **kwargs): pass

    # target = Target()
    # sec_ref = column_element.section_view(target, column, origin=(0.0, 0.0), title="Column Section C1")
    # elev_ref = column_element.elevation_view(target, column, origin=(0.0, -150.0), title="Column Elevation C1")

    # print(f"Direct section_view references: {sec_ref}")
    # print(f"Direct elevation_view references: {elev_ref}")


if __name__ == "__main__":
    main()
