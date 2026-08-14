"""
struct_draw.adapters.struct_core_adapter — Convert struct_core schemas into DXF drawings.

Translates struct_core.detailing_result.DetailingResult and
struct_core.design_result.DesignResult objects into DXF drawings via
struct_draw element renderers.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Union

from struct_core import DetailingResult, DesignResult, Project, StructuralModel
from struct_draw.core.data import (
    BeamData,
    ColumnData,
    FootingData,
    GeometrySection,
    Rebar,
    ScheduleRow,
    SlabData,
    Stirrup,
)
from struct_draw.core.document import new_drawing, register_all_styles
from struct_draw.elements import beam, column, footing, slab
from struct_draw.style import (
    default_blocks,
    default_dimension_styles,
    default_layers,
    default_linetypes,
    default_text_styles,
)


def draw_from_core(
    detailing_or_project: Union[DetailingResult, Project],
    design_result: Optional[DesignResult] = None,
    model_or_project: Optional[Union[StructuralModel, Project]] = None,
) -> Dict[str, Any]:
    """
    Render struct_core DetailingResult & DesignResult into DXF drawing objects.

    Parameters
    ----------
    detailing_or_project : DetailingResult or Project
        The detailing result container or top-level Project.
    design_result : DesignResult, optional
        Matching design result container.
    model_or_project : StructuralModel or Project, optional
        Matching structural model or project container.

    Returns
    -------
    Dict[str, Any]
        Dictionary containing:
        - "drawing": ezdxf.Drawing object containing all rendered member section views.
        - "data": Dictionary of member data objects (BeamData, ColumnData, etc.).
        - "elements_drawn": Number of elements drawn.
    """
    detailing_res = None
    if isinstance(detailing_or_project, Project):
        detailing_res = detailing_or_project.detailing_result
        if design_result is None:
            design_result = detailing_or_project.design_result
        if model_or_project is None:
            model_or_project = detailing_or_project.model
    else:
        detailing_res = detailing_or_project

    if detailing_res is None or not detailing_res.element_results:
        doc = _new_doc()
        return {"drawing": doc, "data": {}, "elements_drawn": 0}

    model = model_or_project.model if isinstance(model_or_project, Project) else model_or_project

    doc = _new_doc()
    msp = doc.modelspace()

    member_data_map: Dict[Union[int, str], Any] = {}
    x_offset = 0.0
    elements_drawn = 0

    for elem_id, elem_detailing in detailing_res.element_results.items():
        elem_design = design_result.element_results.get(elem_id) if design_result and design_result.element_results else None

        member_type = getattr(elem_detailing, "member_type", "beam").lower()

        if member_type == "beam":
            beam_data = _element_to_beam_data(elem_id, elem_detailing, elem_design, model)
            beam.section_view(msp, beam_data, origin=(x_offset, 0.0), title=f"SECTION B-{elem_id}")
            member_data_map[elem_id] = beam_data
            x_offset += beam_data.section.width_in + 30.0
            elements_drawn += 1

        elif member_type == "column":
            col_data = _element_to_column_data(elem_id, elem_detailing, elem_design, model)
            column.section_view(msp, col_data, origin=(x_offset, 0.0), title=f"COLUMN {elem_id}")
            member_data_map[elem_id] = col_data
            x_offset += col_data.section.width_in + 30.0
            elements_drawn += 1

    return {
        "drawing": doc,
        "data": member_data_map,
        "elements_drawn": elements_drawn,
    }


def _new_doc() -> Any:
    """Create a fully-styled DXF document, mirroring _render_dxf in struct_draw.backends."""
    doc = new_drawing()
    register_all_styles(
        doc,
        layers=default_layers(),
        linetypes=default_linetypes(),
        text_styles=default_text_styles(),
        dimension_styles=default_dimension_styles(is_metric=False),
        blocks=default_blocks(),
    )
    return doc


def _element_to_beam_data(
    elem_id: Union[int, str],
    elem_detailing: Any,
    elem_design: Optional[Any],
    model: Optional[Any],
) -> BeamData:
    """Convert struct_core ElementDetailingResult -> struct_draw BeamData."""
    # Find section geometry
    w = 12.0
    d = 18.0
    cover = 1.5

    bar_layout = getattr(elem_detailing, "bar_layout", None)
    schedule = getattr(elem_detailing, "bar_schedule", None)

    top_rebars = []
    bottom_rebars = []
    stirrup_obj = Stirrup(size="#3", spacing_in=6.0, legs=2, width_in=w - 2 * cover, height_in=d - 2 * cover)

    if bar_layout:
        # Bottom layers
        if hasattr(bar_layout, "bottom_layers") and bar_layout.bottom_layers:
            for layer in bar_layout.bottom_layers:
                for b in getattr(layer, "bars", []):
                    top_rebars.append(
                        Rebar(
                            mark=getattr(b, "mark", "B1"),
                            size=f"#{getattr(b, 'size', 8)}",
                            quantity=getattr(b, "count", 3),
                            length_in=getattr(b, "length", 240.0),
                            remarks="BOT",
                        )
                    )

        # Top layers
        if hasattr(bar_layout, "top_layers") and bar_layout.top_layers:
            for layer in bar_layout.top_layers:
                for b in getattr(layer, "bars", []):
                    bottom_rebars.append(
                        Rebar(
                            mark=getattr(b, "mark", "T1"),
                            size=f"#{getattr(b, 'size', 4)}",
                            quantity=getattr(b, "count", 2),
                            length_in=getattr(b, "length", 240.0),
                            remarks="TOP",
                        )
                    )

        # Stirrups
        if hasattr(bar_layout, "stirrups") and bar_layout.stirrups:
            st = bar_layout.stirrups[0]
            stirrup_obj = Stirrup(
                size=f"#{getattr(st, 'size', 3)}",
                spacing_in=float(getattr(st, "spacing", 6.0)),
                legs=int(getattr(st, "legs", 2)),
                width_in=w - 2.0 * cover,
                height_in=d - 2.0 * cover,
            )

    if not top_rebars:
        top_rebars = [Rebar(mark="B1", size="#8", quantity=3, remarks="BOT")]
    if not bottom_rebars:
        bottom_rebars = [Rebar(mark="T1", size="#4", quantity=2, remarks="TOP")]

    sched_rows = []
    if schedule and hasattr(schedule, "items"):
        for item in schedule.items:
            b_size = getattr(item, "bar_size", getattr(item, "size", 8))
            b_size_str = f"#{b_size}" if isinstance(b_size, int) or not str(b_size).startswith("#") else str(b_size)
            b_qty = getattr(item, "quantity", getattr(item, "count", 1))
            sched_rows.append(
                ScheduleRow(
                    mark=getattr(item, "mark", ""),
                    size=b_size_str,
                    quantity=int(b_qty),
                    length_in=float(getattr(item, "cut_length", 240.0)),
                    remarks=getattr(item, "shape_code", ""),
                )
            )

    return BeamData(
        name=f"B{elem_id}",
        section=GeometrySection(width_in=w, depth_in=d, cover_in=cover),
        top_bars=tuple(bottom_rebars),
        bottom_bars=tuple(top_rebars),
        stirrups=stirrup_obj,
        schedule=tuple(sched_rows),
    )


def _element_to_column_data(
    elem_id: Union[int, str],
    elem_detailing: Any,
    elem_design: Optional[Any],
    model: Optional[Any],
) -> ColumnData:
    """Convert struct_core ElementDetailingResult -> struct_draw ColumnData."""
    w = 16.0
    d = 16.0
    cover = 1.5

    bar_layout = getattr(elem_detailing, "bar_layout", None)
    bars_list = []
    tie_obj = Stirrup(size="#3", spacing_in=12.0, legs=2, width_in=w - 2 * cover, height_in=d - 2 * cover)

    if bar_layout:
        if hasattr(bar_layout, "top_layers") and bar_layout.top_layers:
            for layer in bar_layout.top_layers:
                for b in getattr(layer, "bars", []):
                    bars_list.append(
                        Rebar(
                            mark=getattr(b, "mark", "C1"),
                            size=f"#{getattr(b, 'size', 8)}",
                            quantity=getattr(b, "count", 8),
                            length_in=getattr(b, "length", 144.0),
                        )
                    )

        if hasattr(bar_layout, "stirrups") and bar_layout.stirrups:
            st = bar_layout.stirrups[0]
            tie_obj = Stirrup(
                size=f"#{getattr(st, 'size', 3)}",
                spacing_in=float(getattr(st, "spacing", 12.0)),
                legs=int(getattr(st, "legs", 2)),
                width_in=w - 2.0 * cover,
                height_in=d - 2.0 * cover,
            )

    if not bars_list:
        bars_list = [Rebar(mark="C1", size="#8", quantity=8)]

    return ColumnData(
        name=f"C{elem_id}",
        section=GeometrySection(width_in=w, depth_in=d, cover_in=cover),
        longitudinal_bars=tuple(bars_list),
        stirrups=tie_obj,
    )
