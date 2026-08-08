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
    ColumnData,
    CombinedFootingData,
    FootingData,
    MemberType,
    SlabData,
    StaircaseData,
)
from struct_draw.core.document import new_drawing, register_all_styles
from struct_draw.elements import (
    beam,
    column,
    combined_footing,
    footing,
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
    is_metric = False
    if hasattr(data, "is_metric"):
        is_metric = bool(data.is_metric)
    elif hasattr(data, "length_in"):
        is_metric = float(data.length_in) >= 300.0
    elif hasattr(data, "section") and hasattr(data.section, "width_in"):
        is_metric = float(data.section.width_in) >= 300.0

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

    msp = doc.modelspace()

    if isinstance(data, BeamData):
        beam.section_view(msp, data)
        metadata["view"] = "section"
    elif isinstance(data, FootingData):
        footing.section_view(msp, data)
        footing_margin = 800.0 if is_metric else 35.0
        y_offset = -(data.footing_depth_in + data.plinth_height_in + data.width_in / 2.0 + footing_margin)
        footing.plan_view(msp, data, origin=(0.0, y_offset))
        metadata["views"] = ["section", "plan"]
    elif isinstance(data, CombinedFootingData):
        combined_footing.section_view(msp, data)
        cf_margin = 800.0 if is_metric else 35.0
        y_offset = -(data.footing_depth_in + data.plinth_height_in + data.width_in / 2.0 + cf_margin)
        combined_footing.plan_view(msp, data, origin=(0.0, y_offset))
        metadata["views"] = ["section", "plan"]
    elif isinstance(data, ColumnData):
        column.section_view(msp, data)
        y_offset = -2500.0 if is_metric else -100.0
        column.elevation_view(msp, data, origin=(0.0, y_offset))
        metadata["views"] = ["section", "elevation"]
    elif isinstance(data, StaircaseData):
        staircase.plan_view(msp, data)
        staircase_margin = 1000.0 if is_metric else 50.0
        y_offset = -(data.flight_length_in + staircase_margin)
        staircase.section_view(msp, data, origin=(0.0, y_offset))
        metadata["views"] = ["plan", "section"]
    elif isinstance(data, SlabData):
        slab.plan_view(msp, data)
        slab_margin = 1000.0 if is_metric else 50.0
        y_offset = -(data.width_in + slab_margin)
        slab.section_view(msp, data, origin=(0.0, y_offset))
        metadata["views"] = ["plan", "section"]
    else:
        raise BackendError(
            f"Unsupported data type: {type(data).__name__}. "
            f"Expected one of: BeamData, FootingData, ColumnData, "
            f"StaircaseData, SlabData."
        )

    return DrawingResult(backend="dxf", document=doc, metadata=metadata)


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


def save_dxf(data: Any, path: str | Path) -> Path:
    """Render ``data`` and save it as a DXF file. Returns the saved path."""
    result = render(data, backend="dxf")
    return result.save(path)


__all__ = ["DrawingResult", "render", "save_dxf", "MemberType"]