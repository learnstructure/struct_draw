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

from struct_draw.core import data, document, primitives, composite, sheet, viewport, geometry, stirrup, units  # noqa: F401
from struct_draw.core.units import (
    DrawingScale,
    DrawingUnit,
    SCALE_1_10,
    SCALE_1_20,
    SCALE_1_25,
    SCALE_1_50,
    SCALE_1_100,
    SCALE_1_IN,
    SCALE_1_2_IN,
    SCALE_1_4_IN,
    SCALE_1_8_IN,
    SCALE_3_4_IN,
    SCALE_3_IN,
    drawing_unit_from_core,
)
from struct_draw.core.data import (
    BeamData,
    ColumnData,
    CombinedFootingData,
    FootingData,
    GeometrySection,
    IsolatedFootingData,
    MemberType,
    Rebar,
    ScheduleRow,
    ScheduleTableData,
    SlabData,
    StaircaseData,
    Stirrup,
)
from struct_draw.core.document import Document
from struct_draw.core.sheet import PaperSize, Sheet, SheetSet
from struct_draw.core.stirrup import StirrupGeometry, draw_double_line_stirrup
from struct_draw.core.viewport import ViewKind, Viewport, ViewportLayout

__all__ = [
    "data",
    "document",
    "primitives",
    "composite",
    "sheet",
    "viewport",
    "geometry",
    "stirrup",
    "units",
    "DrawingUnit",
    "DrawingScale",
    "drawing_unit_from_core",
    "SCALE_1_10",
    "SCALE_1_20",
    "SCALE_1_25",
    "SCALE_1_50",
    "SCALE_1_100",
    "SCALE_1_IN",
    "SCALE_1_2_IN",
    "SCALE_1_4_IN",
    "SCALE_1_8_IN",
    "SCALE_3_4_IN",
    "SCALE_3_IN",
    "BeamData",
    "ColumnData",
    "CombinedFootingData",
    "IsolatedFootingData",
    "FootingData",
    "GeometrySection",
    "MemberType",
    "Rebar",
    "ScheduleRow",
    "ScheduleTableData",
    "SlabData",
    "StaircaseData",
    "Stirrup",
    "StirrupGeometry",
    "draw_double_line_stirrup",
    "Document",
    "PaperSize",
    "Sheet",
    "SheetSet",
    "ViewKind",
    "Viewport",
    "ViewportLayout",
]