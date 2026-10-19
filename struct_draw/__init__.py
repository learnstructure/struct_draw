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
from struct_draw.adapters.struct_core_adapter import (
    create_general_frame_data_from_model,
    draw_frame_elevation_from_core,
    draw_framing_plan_from_core,
    draw_from_core,
    draw_general_frame_from_core,
)
from struct_draw.backends import DrawingResult, render, save_dxf

# Data classes (commonly used).
from struct_draw.core.data import (
    BeamData,
    BeamProfileData,
    BeamProfileSpan,
    ColumnData,
    ColumnScheduleData,
    CombinedFootingData,
    IsolatedFootingData,
    FootingData,
    FrameElevationData,
    FrameGridLine,
    FrameLevelLine,
    FrameMember,
    FrameNode,
    FramingPlanData,
    GeneralFrameData,
    GeometrySection,
    MemberType,
    Rebar,
    ScheduleRow,
    ScheduleTableData,
    SlabData,
    StaircaseData,
    Stirrup,
    TrussData,
)
from struct_draw.core.composite import draw_schedule_table
from struct_draw.core.stirrup import StirrupGeometry, draw_double_line_stirrup
from struct_draw.core.units import (
    DrawingScale,
    DrawingUnit,
    SCALE_1_10,
    SCALE_1_20,
    SCALE_1_25,
    SCALE_1_30,
    SCALE_1_50,
    SCALE_1_100,
    SCALE_1_IN,
    SCALE_1_2_IN,
    SCALE_1_4_IN,
    SCALE_1_8_IN,
    SCALE_3_4_IN,
    SCALE_3_IN,
    default_scale_for_view,
    drawing_unit_from_core,
)
from struct_draw.style.annotation_config import AnnotationConfig, DEFAULT_ANNOTATION_CONFIG


__all__ = [
    "__version__",
    # Units & Scales
    "DrawingUnit",
    "DrawingScale",
    "AnnotationConfig",
    "DEFAULT_ANNOTATION_CONFIG",
    "drawing_unit_from_core",
    "default_scale_for_view",
    "SCALE_1_10",
    "SCALE_1_20",
    "SCALE_1_25",
    "SCALE_1_30",
    "SCALE_1_50",
    "SCALE_1_100",
    "SCALE_1_IN",
    "SCALE_1_2_IN",
    "SCALE_1_4_IN",
    "SCALE_1_8_IN",
    "SCALE_3_4_IN",
    "SCALE_3_IN",
    # Top-level
    "DrawingResult",
    "render",
    "save_dxf",
    "draw_from_core",
    "draw_general_frame_from_core",
    "draw_framing_plan_from_core",
    "draw_frame_elevation_from_core",
    "create_general_frame_data_from_model",
    # Data
    "BeamData",
    "BeamProfileData",
    "BeamProfileSpan",
    "ColumnData",
    "ColumnScheduleData",
    "CombinedFootingData",
    "IsolatedFootingData",
    "FootingData",
    "FrameElevationData",
    "FrameGridLine",
    "FrameLevelLine",
    "FrameMember",
    "FrameNode",
    "FramingPlanData",
    "GeneralFrameData",
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
    "draw_schedule_table",
    "TrussData",
]