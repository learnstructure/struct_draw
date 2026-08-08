"""struct_draw — Drawing generation for the Structural Engineering Ecosystem.

The dedicated drawing-generation package of the Structural
Engineering Ecosystem. Consumes ``DesignResult`` /
``DetailingResult`` objects produced by ``aci318`` (and any
future engineering packages) and renders them into drawing
files.

DXF is the first-class supported format. PDF / IFC / SVG are
planned.

The v2 architecture replaces the v1 "flat DrawEntity" pipeline
with a **drawing-side core** that:

* defines plain data classes (``BeamData``, ``FootingData``, ...)
  in :mod:`struct_draw.core.data`,
* exposes direct drawing primitives in
  :mod:`struct_draw.core.primitives`,
* supplies reusable rebar / concrete drawing helpers in
  :mod:`struct_draw.core.composite`,
* defines drawing-side style registries in :mod:`struct_draw.style`,
* exposes the user-facing element library in
  :mod:`struct_draw.elements`,
* translates producer results into dataclasses in
  :mod:`struct_draw.adapters`,
* writes DXF files via :mod:`struct_draw.backends`.

Public entry points:

* :func:`struct_draw.render` — top-level render dispatcher.
* :func:`struct_draw.save_dxf` — convenience DXF saver.
* Element library: :mod:`struct_draw.elements` (``beam``,
  ``column``, ``footing``, ``slab``, ``staircase``).
* Style registries: :mod:`struct_draw.style`.
* Core data classes: :mod:`struct_draw.core.data`.
"""

from struct_draw.version import __version__

# Top-level entry points.
from struct_draw.backends import DrawingResult, render, save_dxf

# Data classes (commonly used).
from struct_draw.core.data import (
    BeamData,
    ColumnData,
    FootingData,
    GeometrySection,
    MemberType,
    Rebar,
    ScheduleRow,
    SlabData,
    StaircaseData,
    Stirrup,
)


__all__ = [
    "__version__",
    # Top-level
    "DrawingResult",
    "render",
    "save_dxf",
    # Data
    "BeamData",
    "ColumnData",
    "FootingData",
    "GeometrySection",
    "MemberType",
    "Rebar",
    "ScheduleRow",
    "SlabData",
    "StaircaseData",
    "Stirrup",
]