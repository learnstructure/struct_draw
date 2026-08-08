"""struct_draw.core — Drawing primitives, data, and document helpers.

The v2 architecture replaces the v1 "flat DrawEntity" pipeline with a
**drawing-side core** that:

* defines plain data classes (``BeamData``, ``FootingData``, ...) in
  :mod:`struct_draw.core.data`,
* provides thin ezdxf wrappers in :mod:`struct_draw.core.document`,
* exposes direct drawing primitives in :mod:`struct_draw.core.primitives`,
* supplies reusable rebar / concrete drawing helpers in
  :mod:`struct_draw.core.composite`,
* declares sheet / viewport / paper-size data classes in
  :mod:`struct_draw.core.sheet` and :mod:`struct_draw.core.viewport`,
* provides 2D geometry helpers in :mod:`struct_draw.core.geometry`.

Everything above this layer (``elements``, ``adapters``, ``backends``)
imports from :mod:`struct_draw.core`. Nothing below this layer
imports from above.
"""

from struct_draw.core import data, document, primitives, composite, sheet, viewport, geometry  # noqa: F401
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
from struct_draw.core.document import Document
from struct_draw.core.sheet import PaperSize, Sheet, SheetSet
from struct_draw.core.viewport import ViewKind, Viewport, ViewportLayout

__all__ = [
    "data",
    "document",
    "primitives",
    "composite",
    "sheet",
    "viewport",
    "geometry",
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
    "Document",
    "PaperSize",
    "Sheet",
    "SheetSet",
    "ViewKind",
    "Viewport",
    "ViewportLayout",
]