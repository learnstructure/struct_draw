"""Example 1 — Render a hand-built beam section to DXF.

The smallest end-to-end example: build a :class:`BeamData`
directly, hand it to :func:`struct_draw.render`, and save the
resulting DXF to ``output_beam_section.dxf``.
"""

from __future__ import annotations

from pathlib import Path

import struct_draw as sd
from struct_draw.core.data import (
    BeamData,
    GeometrySection,
    Rebar,
    ScheduleRow,
    Stirrup,
)


def main() -> None:
    beam_data = BeamData(
        name="B1",
        section=GeometrySection(width_in=12.0, depth_in=24.0, cover_in=1.5),
        top_bars=(
            Rebar(mark="T1", size="#5", quantity=2, length_in=240.0),
        ),
        bottom_bars=(
            Rebar(mark="B1", size="#5", quantity=3, length_in=240.0),
        ),
        stirrups=Stirrup(size="#3", spacing_in=6.0, legs=2),
        schedule=(
            ScheduleRow(mark="T1", size="#5", quantity=2, length_in=240.0, remarks="TOP"),
            ScheduleRow(mark="B1", size="#5", quantity=3, length_in=240.0, remarks="BOT"),
            ScheduleRow(mark="S1", size="#3", quantity=40, length_in=72.0, remarks="STIR."),
        ),
        length_in=240.0,
    )

    out_path = Path("output_beam_section.dxf")
    sd.save_dxf(beam_data, out_path)
    print(f"Saved {out_path} (backend=dxf)")


if __name__ == "__main__":
    main()