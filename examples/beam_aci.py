"""Example 2 — Build a beam drawing from a fake ACI 318 result.

This example shows the **full v2 pipeline**:

  1. Build (or receive) an ACI 318 ``BeamDesignResult`` /
     ``BeamDetailingResult`` pair.
  2. Run it through :func:`struct_draw.adapters.aci318.from_beam_result`
     to get a plain :class:`struct_draw.core.data.BeamData`.
  3. Render the dataclass via :func:`struct_draw.save_dxf`.

The "ACI 318 result" object here is a plain Python namespace
(since ``struct_draw`` deliberately does not import ``aci318``).
In real use, swap the dummy builder with the actual
``aci318.design_beam(...)`` call.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import struct_draw as sd
from struct_draw.adapters.aci318 import from_beam_result


def make_fake_aci318_result():
    """Build a fake ``BeamDesignResult`` + ``BeamDetailingResult`` pair."""
    # ACI 318 uses US Imperial units (dimensions in inches)
    section = SimpleNamespace(
        width=12.0,     # 12 inches (1.0 ft)
        depth=24.0,     # 24 inches (2.0 ft)
        cover=1.5,      # 1.5 inches clear cover
    )
    design = SimpleNamespace(
        name="B2",
        section=section,
        length=300.0,   # 300 inches (25.0 ft span)
        flexure=SimpleNamespace(As_top=0.62, As_bottom=0.93),
        shear=SimpleNamespace(stirrup_size="#3", stirrup_spacing=6.0),
    )
    detailing = SimpleNamespace(
        top_bars=(
            SimpleNamespace(mark="T1", size="#5", quantity=2, length=300.0),  # 300 in
        ),
        bottom_bars=(
            SimpleNamespace(mark="B1", size="#5", quantity=3, length=300.0),  # 300 in
        ),
        schedule_rows=(
            SimpleNamespace(mark="T1", size="#5", qty=2, length=300.0, remarks="TOP"),
            SimpleNamespace(mark="B1", size="#5", qty=3, length=300.0, remarks="BOT"),
        ),
    )
    return design, detailing


def main() -> None:
    design, detailing = make_fake_aci318_result()

    # Adapter turns producer results into a plain struct_draw dataclass.
    beam_data = from_beam_result((design, detailing))

    out_path = Path("output_beam_from_aci318.dxf")
    sd.save_dxf(beam_data, out_path)
    print(f"Saved {out_path} (beam name: {beam_data.name}, "
          f"section: {beam_data.section.width_in}x{beam_data.section.depth_in}\")")


if __name__ == "__main__":
    main()