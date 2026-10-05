"""struct_draw.backends — Drawing-format backends.

Currently ships a single backend (``dxf``) that produces DXF
files via ``ezdxf``. Future backends (PDF, IFC, SVG) will live
alongside this one.

The top-level :func:`render` function dispatches a
``(data, target)`` pair to the right backend based on the
``data`` member type and the configured default backend.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from struct_draw.core.data import (
    BeamData,
    BeamProfileData,
    ColumnData,
    CombinedFootingData,
    FootingData,
    FrameElevationData,
    FramingPlanData,
    GeneralFrameData,
    MemberType,
    ScheduleTableData,
    SlabData,
    StaircaseData,
    TrussData,
)
from struct_draw.core.document import new_drawing, register_all_styles
from struct_draw.elements import (
    beam,
    beam_profile,
    column,
    combined_footing,
    footing,
    general_frame,
    slab,
    staircase,
)
from struct_draw.style import (
    default_blocks,
    default_dimension_styles,
    default_layers,
    default_linetypes,
    default_text_styles,
)
from struct_draw.utils.exceptions import BackendError


# ---------------------------------------------------------------------------
# Public result
# ---------------------------------------------------------------------------


@dataclass
class DrawingResult:
    """A rendered drawing ready to save.

    Attributes
    ----------
    backend
        Name of the backend that produced this result (``"dxf"``).
    document
        The underlying backend-specific object (an ``ezdxf.Drawing``
        for the DXF backend).
    metadata
        Free-form metadata describing what was drawn (sheet name,
        element counts, source data class names, etc.).
    """

    backend: str
    document: Any
    metadata: dict[str, Any]

    @property
    def doc(self) -> Any:
        """Alias for document."""
        return self.document

    def save(self, path: str | Path) -> Path:
        """Persist the drawing to ``path`` (delegates to the backend)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if self.backend == "dxf":
            self.document.saveas(str(path))
        else:
            raise BackendError(f"Unknown backend {self.backend!r}")
        return path


# ---------------------------------------------------------------------------
# Top-level render function
# ---------------------------------------------------------------------------


def render(data: Any, *, backend: str = "dxf") -> DrawingResult:
    """Render ``data`` into a :class:`DrawingResult`.

    Dispatches to the backend named by ``backend`` (currently only
    ``"dxf"`` is supported). For the DXF backend, ``data`` can be
    any of the :mod:`struct_draw.core.data` member dataclasses.
    """
    if backend != "dxf":
        raise BackendError(f"Unknown backend {backend!r}; supported: 'dxf'.")
    return _render_dxf(data)


# ---------------------------------------------------------------------------
# DXF backend
# ---------------------------------------------------------------------------


def _render_dxf(data: Any) -> DrawingResult:
    """Render ``data`` to a populated ``ezdxf.Drawing``.

    The backend:

    1. Creates a fresh ``ezdxf.Drawing`` (``R2018``, ``setup=True``).
    2. Registers the default style registries (layers, linetypes,
       text styles, dimension styles, blocks).
    3. Dispatches ``data`` to the matching element function based
       on its type.
    """
    scale = getattr(data, "scale", None)
    unit = getattr(data, "unit", None)

    is_metric = False
    if unit is not None:
        try:
            from struct_draw.core.units import DrawingUnit
            du = DrawingUnit.from_str(unit)
            is_metric = (du == DrawingUnit.MM)
        except Exception:
            pass
    elif hasattr(data, "is_metric"):
        is_metric = bool(data.is_metric)
    elif hasattr(data, "section") and hasattr(data.section, "width_in"):
        is_metric = float(data.section.width_in) >= 100.0 or float(data.section.depth_in) >= 100.0
    elif hasattr(data, "length_in"):
        is_metric = float(data.length_in) >= 1000.0

    doc = new_drawing()
    register_all_styles(
        doc,
        layers=default_layers(),
        linetypes=default_linetypes(),
        text_styles=default_text_styles(),
        dimension_styles=default_dimension_styles(is_metric=is_metric),
        blocks=default_blocks(),
    )

    metadata: dict[str, Any] = {"element": type(data).__name__, "is_metric": is_metric}
    if scale is not None:
        metadata["scale"] = str(scale)
    if unit is not None:
        metadata["unit"] = str(unit)

    msp = doc.modelspace()

    extra_kw: dict[str, Any] = {}
    if scale is not None:
        extra_kw["scale"] = scale
    if unit is not None:
        extra_kw["unit"] = unit

    if isinstance(data, BeamData):
        beam.section_view(msp, data, **extra_kw)
        metadata["view"] = "section"
    elif isinstance(data, BeamProfileData):
        beam_profile.drawing(msp, data, **extra_kw)
        metadata["views"] = ["profile", "section"]
    elif isinstance(data, FootingData):
        ref_sec = footing.section_view(msp, data, **extra_kw)
        footing_margin = 800.0 if is_metric else 35.0
        y_offset = -(data.footing_depth_in + data.plinth_height_in + data.width_in / 2.0 + footing_margin)
        ref_plan = footing.plan_view(msp, data, origin=(0.0, y_offset), **extra_kw)
        views = ["section", "plan"]
        if data.schedule:
            from struct_draw.core.composite import draw_schedule_table
            plan_bb = ref_plan.get("bounding_box", (0.0, y_offset - data.width_in / 2.0, 0.0, y_offset))
            sched_y = plan_bb[1] - footing_margin
            draw_schedule_table(
                msp,
                ScheduleTableData(
                    title=f"{data.name} REBAR SCHEDULE",
                    rows=data.schedule,
                    unit="mm" if is_metric else "in",
                    scale=scale,
                ),
                origin=(0.0, sched_y),
                align="center",
                **extra_kw,
            )
            views.append("schedule")
        metadata["views"] = views
    elif isinstance(data, CombinedFootingData):
        ref_sec = combined_footing.section_view(msp, data, **extra_kw)
        cf_margin = 800.0 if is_metric else 35.0
        y_offset = -(data.footing_depth_in + data.plinth_height_in + data.width_in / 2.0 + cf_margin)
        ref_plan = combined_footing.plan_view(msp, data, origin=(0.0, y_offset), **extra_kw)
        views = ["section", "plan"]
        if data.schedule:
            from struct_draw.core.composite import draw_schedule_table
            plan_bb = ref_plan.get("bounding_box", (0.0, y_offset - data.width_in / 2.0, 0.0, y_offset))
            sched_y = plan_bb[1] - cf_margin
            center_x = (-data.proj_left_in + (data.col_spacing_in + data.proj_right_in)) / 2.0
            draw_schedule_table(
                msp,
                ScheduleTableData(
                    title=f"{data.name} REBAR SCHEDULE",
                    rows=data.schedule,
                    unit="mm" if is_metric else "in",
                    scale=scale,
                ),
                origin=(center_x, sched_y),
                align="center",
                **extra_kw,
            )
            views.append("schedule")
        metadata["views"] = views
    elif isinstance(data, ColumnData):
        refs = column.drawing(msp, data, **extra_kw)
        views = ["elevation", "section"]
        if data.schedule or (isinstance(refs, dict) and "schedule" in refs):
            views.append("schedule")
        metadata["views"] = views
    elif isinstance(data, StaircaseData):
        staircase.section_view(msp, data, **extra_kw)
        staircase_margin = 1500.0 if is_metric else 60.0
        y_offset = -(data.flight_width_in * 2.5 + staircase_margin)
        staircase.plan_view(msp, data, origin=(0.0, y_offset), **extra_kw)
        metadata["views"] = ["section", "plan"]
    elif isinstance(data, SlabData):
        slab.plan_view(msp, data, **extra_kw)
        slab_margin = 1000.0 if is_metric else 50.0
        y_offset = -(data.width_in + slab_margin)
        slab.section_view(msp, data, origin=(0.0, y_offset), **extra_kw)
        metadata["views"] = ["plan", "section"]
    elif isinstance(data, FramingPlanData):
        general_frame.plan_view(msp, data, **extra_kw)
        metadata["view"] = "framing_plan"
    elif isinstance(data, FrameElevationData):
        general_frame.elevation_view(msp, data, **extra_kw)
        metadata["view"] = "frame_elevation"
    elif isinstance(data, TrussData):
        general_frame.truss_view(msp, data, **extra_kw)
        metadata["view"] = "truss_outline"
    elif isinstance(data, GeneralFrameData):
        general_frame.drawing(msp, data, **extra_kw)
        metadata["view"] = data.view_mode
    elif isinstance(data, ScheduleTableData):
        from struct_draw.core.composite import draw_schedule_table
        draw_schedule_table(msp, data, **extra_kw)
        metadata["view"] = "schedule_table"
    else:
        raise BackendError(
            f"Unsupported data type: {type(data).__name__}. "
            f"Expected one of: BeamData, BeamProfileData, FootingData, "
            f"CombinedFootingData, ColumnData, StaircaseData, SlabData, "
            f"GeneralFrameData, FramingPlanData, FrameElevationData, TrussData, "
            f"ScheduleTableData."
        )

    return DrawingResult(backend="dxf", document=doc, metadata=metadata)


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


def save_dxf(data: Any, path: str | Path) -> Path:
    """Render ``data`` and save it as a DXF file. Returns the saved path."""
    if isinstance(data, DrawingResult):
        return data.save(path)
    if hasattr(data, "saveas"):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data.saveas(str(path))
        return path
    result = render(data, backend="dxf")
    return result.save(path)


__all__ = ["DrawingResult", "render", "save_dxf", "MemberType"]