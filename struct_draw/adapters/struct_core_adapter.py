"""
struct_draw.adapters.struct_core_adapter — Convert struct_core schemas into DXF drawings.

Translates struct_core.detailing_result.DetailingResult and
struct_core.design_result.DesignResult objects into DXF drawings via
struct_draw element renderers.

Supports all seven detailed member types (Beam, BeamProfile, Footing,
CombinedFooting, Column, Staircase, Slab) with dynamic geometry extraction,
plus General Drawing generation (framing plan & frame elevation without rebar)
from StructuralModel or Project.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

try:
    from struct_core import DetailingResult, DesignResult, Project, StructuralModel
except ImportError:
    class DetailingResult:  # type: ignore[no-redef]
        pass

    class DesignResult:  # type: ignore[no-redef]
        pass

    class Project:  # type: ignore[no-redef]
        pass

    class StructuralModel:  # type: ignore[no-redef]
        pass

from struct_draw.core.data import (
    BeamData,
    BeamProfileData,
    BeamProfileSpan,
    ColumnData,
    CombinedFootingData,
    FootingData,
    FrameElevationData,
    FrameGridLine,
    FrameLevelLine,
    FrameMember,
    FrameNode,
    FramingPlanData,
    GeneralFrameData,
    GeometrySection,
    Rebar,
    ScheduleRow,
    SlabData,
    StaircaseData,
    Stirrup,
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


def draw_from_core(
    detailing_or_project: Union[DetailingResult, Project, StructuralModel],
    design_result: Optional[DesignResult] = None,
    model_or_project: Optional[Union[StructuralModel, Project]] = None,
    *,
    view_type: str = "auto",
) -> Dict[str, Any]:
    """
    Render struct_core results into DXF drawings.

    Dispatches across all seven supported structural member types:
    Beam, BeamProfile, Footing, CombinedFooting, Column, Staircase, Slab.
    Also handles General Framing drawing generation if detailing is absent or
    view_type="general_frame".

    Parameters
    ----------
    detailing_or_project : DetailingResult, Project, or StructuralModel
        The detailing result container, top-level Project, or StructuralModel.
    design_result : DesignResult, optional
        Matching design result container.
    model_or_project : StructuralModel or Project, optional
        Matching structural model or project container.
    view_type : str, optional
        "auto", "section", "plan", "elevation", "all", or "general_frame".

    Returns
    -------
    Dict[str, Any]
        Dictionary containing:
        - "drawing": ezdxf.Drawing object containing all rendered member views.
        - "data": Dictionary of member data objects (BeamData, ColumnData, etc.).
        - "elements_drawn": Number of elements drawn.
    """
    detailing_res = None
    model = None

    if isinstance(detailing_or_project, Project):
        detailing_res = getattr(detailing_or_project, "detailing_result", None)
        if design_result is None:
            design_result = getattr(detailing_or_project, "design_result", None)
        if model_or_project is None:
            model = getattr(detailing_or_project, "model", None)
    elif isinstance(detailing_or_project, StructuralModel):
        model = detailing_or_project
    else:
        detailing_res = detailing_or_project

    if model_or_project is not None and model is None:
        model = model_or_project.model if isinstance(model_or_project, Project) else model_or_project

    # If general framing requested or no detailing is present but a model exists, generate GA framing drawing
    if view_type == "general_frame" or (detailing_res is None or not getattr(detailing_res, "element_results", None)):
        if model is not None:
            return draw_general_frame_from_core(model, view_mode="both")
        doc = _new_doc(is_metric=False)
        return {"drawing": doc, "data": {}, "elements_drawn": 0}

    # Determine metric context from elements or detailing
    is_metric = _detect_is_metric(detailing_res, model)

    doc = _new_doc(is_metric=is_metric)
    msp = doc.modelspace()

    member_data_map: Dict[Union[int, str], Any] = {}
    x_offset = 0.0
    elements_drawn = 0

    elem_results = getattr(detailing_res, "element_results", {})
    des_results = getattr(design_result, "element_results", {}) if design_result else {}

    for elem_id, elem_detailing in elem_results.items():
        elem_design = des_results.get(elem_id) if des_results else None

        member_type = _determine_member_type(elem_detailing, elem_design, model, elem_id)

        if member_type == "beam":
            beam_data = _element_to_beam_data(elem_id, elem_detailing, elem_design, model)
            beam.section_view(msp, beam_data, origin=(x_offset, 0.0), title=f"SECTION B-{elem_id}")
            member_data_map[elem_id] = beam_data
            step = beam_data.section.width_in + (600.0 if beam_data.is_metric else 30.0)
            x_offset += step
            elements_drawn += 1

        elif member_type == "beam_profile":
            prof_data = _element_to_beam_profile_data(elem_id, elem_detailing, elem_design, model)
            beam_profile.drawing(msp, prof_data, origin=(x_offset, 0.0))
            member_data_map[elem_id] = prof_data
            step = sum(prof_data.spans_in) + (1500.0 if prof_data.is_metric else 60.0)
            x_offset += step
            elements_drawn += 1

        elif member_type == "column":
            col_data = _element_to_column_data(elem_id, elem_detailing, elem_design, model)
            res_col = column.drawing(msp, col_data, origin=(x_offset, 0.0), title=f"COLUMN {elem_id}")
            member_data_map[elem_id] = col_data
            col_bbox = res_col.get("bounding_box", (x_offset, 0.0, x_offset + 100.0, 100.0))
            step = (col_bbox[2] - col_bbox[0]) + (800.0 if col_data.is_metric else 40.0)
            x_offset += step
            elements_drawn += 1

        elif member_type == "footing":
            ftg_data = _element_to_footing_data(elem_id, elem_detailing, elem_design, model)
            footing.section_view(msp, ftg_data, origin=(x_offset, 0.0))
            f_margin = 800.0 if ftg_data.is_metric else 35.0
            y_plan = -(ftg_data.footing_depth_in + ftg_data.plinth_height_in + ftg_data.width_in / 2.0 + f_margin)
            footing.plan_view(msp, ftg_data, origin=(x_offset, y_plan))
            member_data_map[elem_id] = ftg_data
            step = ftg_data.length_in + (1000.0 if ftg_data.is_metric else 40.0)
            x_offset += step
            elements_drawn += 1

        elif member_type == "combined_footing":
            cf_data = _element_to_combined_footing_data(elem_id, elem_detailing, elem_design, model)
            combined_footing.section_view(msp, cf_data, origin=(x_offset, 0.0))
            cf_margin = 800.0 if cf_data.is_metric else 35.0
            y_plan = -(cf_data.footing_depth_in + cf_data.plinth_height_in + cf_data.width_in / 2.0 + cf_margin)
            combined_footing.plan_view(msp, cf_data, origin=(x_offset, y_plan))
            member_data_map[elem_id] = cf_data
            step = cf_data.total_length_in + (1000.0 if cf_data.is_metric else 40.0)
            x_offset += step
            elements_drawn += 1

        elif member_type == "staircase":
            st_data = _element_to_staircase_data(elem_id, elem_detailing, elem_design, model)
            staircase.section_view(msp, st_data, origin=(x_offset, 0.0))
            st_margin = 1500.0 if st_data.is_metric else 60.0
            y_plan = -(st_data.flight_width_in * 2.5 + st_margin)
            staircase.plan_view(msp, st_data, origin=(x_offset, y_plan))
            member_data_map[elem_id] = st_data
            step = st_data.flight_length_in + st_data.bottom_landing_depth_in + st_data.top_landing_depth_in + (1200.0 if st_data.is_metric else 50.0)
            x_offset += step
            elements_drawn += 1

        elif member_type == "slab":
            slab_data = _element_to_slab_data(elem_id, elem_detailing, elem_design, model)
            slab.plan_view(msp, slab_data, origin=(x_offset, 0.0))
            sl_margin = 1000.0 if slab_data.is_metric else 50.0
            y_sec = -(slab_data.width_in + sl_margin)
            slab.section_view(msp, slab_data, origin=(x_offset, y_sec))
            member_data_map[elem_id] = slab_data
            step = slab_data.length_in + (1200.0 if slab_data.is_metric else 50.0)
            x_offset += step
            elements_drawn += 1

    return {
        "drawing": doc,
        "data": member_data_map,
        "elements_drawn": elements_drawn,
    }


def draw_general_frame_from_core(
    model_or_project: Union[StructuralModel, Project],
    *,
    view_mode: str = "both",  # "elevation", "plan", "both"
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate General Arrangement / Framing Drawings (plan and/or elevation outlines of beams, columns, trusses)
    directly from a structural model without rebar details.
    """
    model = model_or_project.model if isinstance(model_or_project, Project) else model_or_project
    frame_data = _model_to_general_frame_data(model, view_mode=view_mode, title=title)

    doc = _new_doc(is_metric=frame_data.is_metric)
    msp = doc.modelspace()

    res = general_frame.drawing(msp, frame_data, origin=(0.0, 0.0))

    return {
        "drawing": doc,
        "data": {"frame": frame_data},
        "elements_drawn": len(frame_data.members),
        "views": res,
    }


def _new_doc(is_metric: bool = False) -> Any:
    """Create a fully-styled DXF document matching struct_draw.backends."""
    doc = new_drawing()
    register_all_styles(
        doc,
        layers=default_layers(),
        linetypes=default_linetypes(),
        text_styles=default_text_styles(),
        dimension_styles=default_dimension_styles(is_metric=is_metric),
        blocks=default_blocks(),
    )
    return doc


def _determine_member_type(elem_detailing: Any, elem_design: Optional[Any], model: Optional[Any], elem_id: Any) -> str:
    """Determine the member type string across detailing, design, model, or type inspection."""
    raw = getattr(elem_detailing, "member_type", None) or getattr(elem_design, "member_type", None)

    if not raw and model:
        elements = getattr(model, "elements", None) or getattr(model, "members", None)
        if isinstance(elements, dict) and elem_id in elements:
            raw = getattr(elements[elem_id], "member_type", None)

    if not raw:
        type_name = type(elem_detailing).__name__.lower()
        for candidate in ("beam_profile", "combined_footing", "footing", "staircase", "column", "slab", "beam"):
            if candidate in type_name:
                raw = candidate
                break

    if not raw:
        raw = "beam"

    raw_str = str(raw).lower()
    if "beam_profile" in raw_str or "continuous_beam" in raw_str or "profile" in raw_str:
        return "beam_profile"
    if "combined_footing" in raw_str or "strip_footing" in raw_str:
        return "combined_footing"
    if "footing" in raw_str or "pad" in raw_str or "isolated" in raw_str:
        return "footing"
    if "column" in raw_str or "pier" in raw_str:
        return "column"
    if "stair" in raw_str:
        return "staircase"
    if "slab" in raw_str or "plate" in raw_str:
        return "slab"
    return "beam"


def _safe_get(obj: Any, keys: Sequence[str], default: Any = None) -> Any:
    """Safely extract the first available key or attribute from an object or dictionary."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        for k in keys:
            if k in obj and obj[k] is not None:
                return obj[k]
        return default
    for k in keys:
        try:
            val = getattr(obj, k, None)
            if val is not None:
                return val
        except Exception:
            pass
    obj_dict = getattr(obj, "__dict__", None)
    if isinstance(obj_dict, dict):
        for k in keys:
            if k in obj_dict and obj_dict[k] is not None:
                return obj_dict[k]
    return default


def _extract_section_properties(
    elem_id: Union[int, str],
    elem_detailing: Any,
    elem_design: Optional[Any],
    model: Optional[Any],
    *,
    default_w: float = 12.0,
    default_d: float = 18.0,
    default_cover: float = 1.5,
    default_length: float = 240.0,
) -> Tuple[float, float, float, float, bool]:
    """
    Extract (width, depth, cover, length, is_metric) dynamically without hardcoding.
    Searches elem_detailing -> elem_design -> model.elements -> model.sections.
    """
    w = None
    d = None
    cover = None
    length = None

    # 1. Search elem_detailing
    sec = _safe_get(elem_detailing, ("section", "geometry_section", "cross_section"))
    if sec is not None:
        w = _safe_get(sec, ("width_in", "width", "b", "bw", "width_mm"))
        d = _safe_get(sec, ("depth_in", "depth", "h", "height", "depth_mm"))
        cover = _safe_get(sec, ("cover_in", "cover", "clear_cover", "cover_mm"))

    if w is None:
        w = _safe_get(elem_detailing, ("width_in", "width", "b", "bw", "section_width"))
    if d is None:
        d = _safe_get(elem_detailing, ("depth_in", "depth", "h", "height", "section_depth"))
    if cover is None:
        cover = _safe_get(elem_detailing, ("cover_in", "cover", "clear_cover"))
    if length is None:
        length = _safe_get(elem_detailing, ("length_in", "length", "span", "span_in", "flight_length_in"))

    # Check bar_layout in elem_detailing if stirrup contains explicit width/height
    bar_layout = getattr(elem_detailing, "bar_layout", None)
    if bar_layout and hasattr(bar_layout, "stirrups") and bar_layout.stirrups:
        st = bar_layout.stirrups[0]
        st_w = _safe_get(st, ("width_in", "width"))
        st_h = _safe_get(st, ("height_in", "height"))
        st_cover = _safe_get(st, ("cover_in", "cover"))
        if st_cover is not None and cover is None:
            cover = float(st_cover)
        if st_w is not None and w is None:
            w = float(st_w) + 2.0 * (cover if cover is not None else default_cover)
        if st_h is not None and d is None:
            d = float(st_h) + 2.0 * (cover if cover is not None else default_cover)

    # 2. Search elem_design
    if elem_design is not None:
        sec_d = _safe_get(elem_design, ("section", "geometry_section", "cross_section"))
        if sec_d is not None:
            if w is None:
                w = _safe_get(sec_d, ("width_in", "width", "b", "bw"))
            if d is None:
                d = _safe_get(sec_d, ("depth_in", "depth", "h", "height"))
            if cover is None:
                cover = _safe_get(sec_d, ("cover_in", "cover", "clear_cover"))
        if w is None:
            w = _safe_get(elem_design, ("width_in", "width", "b", "bw"))
        if d is None:
            d = _safe_get(elem_design, ("depth_in", "depth", "h", "height"))
        if cover is None:
            cover = _safe_get(elem_design, ("cover_in", "cover", "clear_cover"))
        if length is None:
            length = _safe_get(elem_design, ("length_in", "length", "span"))

    # 3. Search model
    if model is not None:
        elements = getattr(model, "elements", None) or getattr(model, "members", None)
        elem_obj = None
        if isinstance(elements, dict):
            elem_obj = elements.get(elem_id)
        elif isinstance(elements, (list, tuple)):
            for candidate in elements:
                if getattr(candidate, "id", None) == elem_id or getattr(candidate, "name", None) == elem_id:
                    elem_obj = candidate
                    break

        if elem_obj is not None:
            # Check length from nodes
            start_node_id = getattr(elem_obj, "start_node", getattr(elem_obj, "node_i", None))
            end_node_id = getattr(elem_obj, "end_node", getattr(elem_obj, "node_j", None))
            nodes = getattr(model, "nodes", None)
            if start_node_id and end_node_id and isinstance(nodes, dict):
                n1 = nodes.get(start_node_id)
                n2 = nodes.get(end_node_id)
                if n1 and n2:
                    dx = getattr(n2, "x", 0.0) - getattr(n1, "x", 0.0)
                    dy = getattr(n2, "y", 0.0) - getattr(n1, "y", 0.0)
                    dz = getattr(n2, "z", 0.0) - getattr(n1, "z", 0.0)
                    calc_len = math.hypot(dx, dy, dz)
                    if calc_len > 0:
                        length = calc_len

            # Check section on elem_obj
            sec_m = getattr(elem_obj, "section", getattr(elem_obj, "cross_section", None))
            if sec_m is not None:
                if w is None:
                    w = _safe_get(sec_m, ("width_in", "width", "b", "bw"))
                if d is None:
                    d = _safe_get(sec_m, ("depth_in", "depth", "h", "height"))
                if cover is None:
                    cover = _safe_get(sec_m, ("cover_in", "cover", "clear_cover"))

            # Check model.sections by section_id
            sec_id = getattr(elem_obj, "section_id", None)
            sections = getattr(model, "sections", getattr(model, "cross_sections", None))
            if sec_id and isinstance(sections, dict) and sec_id in sections:
                s_entry = sections[sec_id]
                if w is None:
                    w = _safe_get(s_entry, ("width_in", "width", "b", "bw"))
                if d is None:
                    d = _safe_get(s_entry, ("depth_in", "depth", "h", "height"))
                if cover is None:
                    cover = _safe_get(s_entry, ("cover_in", "cover", "clear_cover"))

    # Determine metric
    test_w = float(w) if w is not None else default_w
    test_d = float(d) if d is not None else default_d
    test_len = float(length) if length is not None else default_length

    is_metric = test_w >= 100.0 or test_d >= 100.0 or test_len >= 1000.0

    if is_metric:
        final_w = float(w) if w is not None else (default_w * 25.4 if default_w < 50 else default_w)
        final_d = float(d) if d is not None else (default_d * 25.4 if default_d < 50 else default_d)
        final_cover = float(cover) if cover is not None else (default_cover * 25.4 if default_cover < 10 else 40.0)
        final_len = float(length) if length is not None else (default_length * 25.4 if default_length < 200 else default_length)
    else:
        final_w = float(w) if w is not None else default_w
        final_d = float(d) if d is not None else default_d
        final_cover = float(cover) if cover is not None else default_cover
        final_len = float(length) if length is not None else default_length

    return final_w, final_d, final_cover, final_len, is_metric


def _detect_is_metric(detailing_res: Any, model: Any) -> bool:
    """Check if the global project/results use metric (SI mm) units."""
    if hasattr(detailing_res, "is_metric"):
        return bool(detailing_res.is_metric)
    if hasattr(model, "is_metric"):
        return bool(model.is_metric)
    if hasattr(model, "unit_system"):
        return "si" in str(model.unit_system).lower() or "metric" in str(model.unit_system).lower()

    # Check first element result
    if detailing_res and hasattr(detailing_res, "element_results") and detailing_res.element_results:
        first_elem = next(iter(detailing_res.element_results.values()))
        w, d, _, _, is_m = _extract_section_properties(0, first_elem, None, model)
        return is_m
    return False


# ---------------------------------------------------------------------------
# Converters for all 7 detailed member types
# ---------------------------------------------------------------------------


def _element_to_beam_data(
    elem_id: Union[int, str],
    elem_detailing: Any,
    elem_design: Optional[Any],
    model: Optional[Any],
) -> BeamData:
    """Convert struct_core detailing/design/model -> struct_draw BeamData."""
    w, d, cover, length, is_metric = _extract_section_properties(
        elem_id, elem_detailing, elem_design, model, default_w=12.0, default_d=18.0, default_cover=1.5
    )

    bar_layout = getattr(elem_detailing, "bar_layout", None)
    schedule = getattr(elem_detailing, "bar_schedule", None)

    top_rebars: List[Rebar] = []
    bottom_rebars: List[Rebar] = []
    stirrup_size = "T10" if is_metric else "#3"
    stirrup_spacing = 150.0 if is_metric else 6.0
    stirrup_obj = Stirrup(size=stirrup_size, spacing_in=stirrup_spacing, legs=2, width_in=max(1.0, w - 2 * cover), height_in=max(1.0, d - 2 * cover))

    if bar_layout:
        # Bottom layers
        if hasattr(bar_layout, "bottom_layers") and bar_layout.bottom_layers:
            for layer in bar_layout.bottom_layers:
                for b in getattr(layer, "bars", []):
                    b_size = getattr(b, "size", 8 if not is_metric else 20)
                    b_size_str = f"#{b_size}" if not is_metric and not str(b_size).startswith("#") else (f"T{b_size}" if is_metric and not str(b_size).startswith("T") else str(b_size))
                    bottom_rebars.append(
                        Rebar(
                            mark=getattr(b, "mark", "B1"),
                            size=b_size_str,
                            quantity=getattr(b, "count", 3),
                            length_in=getattr(b, "length", length),
                            remarks="BOT",
                        )
                    )

        # Top layers
        if hasattr(bar_layout, "top_layers") and bar_layout.top_layers:
            for layer in bar_layout.top_layers:
                for b in getattr(layer, "bars", []):
                    b_size = getattr(b, "size", 4 if not is_metric else 12)
                    b_size_str = f"#{b_size}" if not is_metric and not str(b_size).startswith("#") else (f"T{b_size}" if is_metric and not str(b_size).startswith("T") else str(b_size))
                    top_rebars.append(
                        Rebar(
                            mark=getattr(b, "mark", "T1"),
                            size=b_size_str,
                            quantity=getattr(b, "count", 2),
                            length_in=getattr(b, "length", length),
                            remarks="TOP",
                        )
                    )

        # Stirrups
        if hasattr(bar_layout, "stirrups") and bar_layout.stirrups:
            st = bar_layout.stirrups[0]
            st_sz = getattr(st, "size", 3 if not is_metric else 10)
            st_sz_str = f"#{st_sz}" if not is_metric and not str(st_sz).startswith("#") else (f"T{st_sz}" if is_metric and not str(st_sz).startswith("T") else str(st_sz))
            stirrup_obj = Stirrup(
                size=st_sz_str,
                spacing_in=float(getattr(st, "spacing", stirrup_spacing)),
                legs=int(getattr(st, "legs", 2)),
                width_in=max(1.0, w - 2.0 * cover),
                height_in=max(1.0, d - 2.0 * cover),
            )

    if not bottom_rebars:
        bottom_rebars = [Rebar(mark="B1", size="T20" if is_metric else "#8", quantity=3, length_in=length, remarks="BOT")]
    if not top_rebars:
        top_rebars = [Rebar(mark="T1", size="T12" if is_metric else "#4", quantity=2, length_in=length, remarks="TOP")]

    sched_rows: List[ScheduleRow] = []
    if schedule and hasattr(schedule, "items"):
        for item in schedule.items:
            b_size = getattr(item, "bar_size", getattr(item, "size", 8 if not is_metric else 20))
            b_size_str = f"#{b_size}" if not is_metric and not str(b_size).startswith("#") else (f"T{b_size}" if is_metric and not str(b_size).startswith("T") else str(b_size))
            b_qty = getattr(item, "quantity", getattr(item, "count", 1))
            sched_rows.append(
                ScheduleRow(
                    mark=getattr(item, "mark", ""),
                    size=b_size_str,
                    quantity=int(b_qty),
                    length_in=float(getattr(item, "cut_length", length)),
                    remarks=getattr(item, "shape_code", ""),
                )
            )

    return BeamData(
        name=f"B{elem_id}",
        section=GeometrySection(width_in=w, depth_in=d, cover_in=cover),
        top_bars=tuple(top_rebars),
        bottom_bars=tuple(bottom_rebars),
        stirrups=stirrup_obj,
        schedule=tuple(sched_rows),
    )


def _element_to_beam_profile_data(
    elem_id: Union[int, str],
    elem_detailing: Any,
    elem_design: Optional[Any],
    model: Optional[Any],
) -> BeamProfileData:
    """Convert struct_core detailing/design -> struct_draw BeamProfileData."""
    w, d, cover, length, is_metric = _extract_section_properties(
        elem_id, elem_detailing, elem_design, model, default_w=12.0, default_d=24.0, default_cover=1.5
    )

    # Spans
    spans_raw = _safe_get(elem_detailing, ("spans", "span_lengths")) or _safe_get(elem_design, ("spans", "span_lengths"))
    if spans_raw and isinstance(spans_raw, (list, tuple)):
        spans_in = [float(s) for s in spans_raw]
    else:
        span_val = length if length > 0 else (6000.0 if is_metric else 240.0)
        spans_in = [span_val, span_val]

    col_w = _safe_get(elem_detailing, ("support_width", "col_width")) or (400.0 if is_metric else 16.0)

    t_bar = Rebar(mark="T1", size="T20" if is_metric else "#6", quantity=2)
    b_bar = Rebar(mark="B1", size="T25" if is_metric else "#8", quantity=3)
    extra_bar = Rebar(mark="TE1", size="T20" if is_metric else "#6", quantity=2)
    stirrup_sz = "T10" if is_metric else "#3"
    s_supp = 100.0 if is_metric else 4.0
    s_mid = 200.0 if is_metric else 8.0

    return BeamProfileData(
        name=f"CB-{elem_id}",
        spans_in=tuple(spans_in),
        beam_depth_in=d,
        beam_width_in=w,
        cover_in=cover,
        col_width_in=float(col_w),
        top_bars=(t_bar,),
        bottom_bars=(b_bar,),
        top_extra_bars=(extra_bar,),
        stirrup=Stirrup(size=stirrup_sz, spacing_in=s_mid),
        support_stirrup_spacing_in=s_supp,
        mid_stirrup_spacing_in=s_mid,
    )


def _element_to_footing_data(
    elem_id: Union[int, str],
    elem_detailing: Any,
    elem_design: Optional[Any],
    model: Optional[Any],
) -> FootingData:
    """Convert struct_core detailing/design -> struct_draw FootingData."""
    length = _safe_get(elem_detailing, ("length_in", "length", "footing_length", "L")) or _safe_get(elem_design, ("length_in", "length", "L"))
    width = _safe_get(elem_detailing, ("width_in", "width", "footing_width", "B")) or _safe_get(elem_design, ("width_in", "width", "B"))
    thickness = _safe_get(elem_detailing, ("thickness_in", "thickness", "mid_thickness_in", "D")) or _safe_get(elem_design, ("thickness_in", "thickness", "D"))
    col_w = _safe_get(elem_detailing, ("col_width_in", "col_width", "column_width")) or (400.0 if (length and length >= 1000) else 16.0)
    col_d = _safe_get(elem_detailing, ("col_depth_in", "col_depth", "column_depth")) or (400.0 if (length and length >= 1000) else 16.0)

    is_metric = False
    if (length and length >= 1000) or (width and width >= 1000) or (thickness and thickness >= 100):
        is_metric = True

    flen = float(length) if length else (2000.0 if is_metric else 84.0)
    fwid = float(width) if width else (2000.0 if is_metric else 84.0)
    fthk = float(thickness) if thickness else (450.0 if is_metric else 18.0)
    edge_thk = float(_safe_get(elem_detailing, ("edge_thickness_in", "edge_thickness")) or (200.0 if is_metric else 10.0))

    bar_dia = float(_safe_get(elem_detailing, ("bar_dia_in", "bar_diameter", "bar_dia")) or (12.0 if is_metric else 0.625))
    bar_sp = float(_safe_get(elem_detailing, ("bar_spacing_in", "bar_spacing")) or (150.0 if is_metric else 6.0))
    cover = float(_safe_get(elem_detailing, ("cover_in", "cover")) or (75.0 if is_metric else 3.0))

    return FootingData(
        name=f"F{elem_id}",
        length_in=flen,
        width_in=fwid,
        mid_thickness_in=fthk,
        edge_thickness_in=edge_thk,
        column_width_in=float(col_w),
        column_depth_in=float(col_d),
        footing_depth_in=1500.0 if is_metric else 60.0,
        plinth_height_in=300.0 if is_metric else 12.0,
        cover_in=cover,
        bar_dia_in=bar_dia,
        bar_spacing_in=bar_sp,
    )


def _element_to_combined_footing_data(
    elem_id: Union[int, str],
    elem_detailing: Any,
    elem_design: Optional[Any],
    model: Optional[Any],
) -> CombinedFootingData:
    """Convert struct_core detailing/design -> struct_draw CombinedFootingData."""
    proj_l = float(_safe_get(elem_detailing, ("proj_left_in", "cantilever_left")) or _safe_get(elem_design, ("proj_left_in", "cantilever_left")) or 30.0)
    proj_r = float(_safe_get(elem_detailing, ("proj_right_in", "cantilever_right")) or _safe_get(elem_design, ("proj_right_in", "cantilever_right")) or 30.0)
    col_sp = float(_safe_get(elem_detailing, ("col_spacing_in", "column_spacing")) or _safe_get(elem_design, ("col_spacing_in", "column_spacing")) or 120.0)
    w = float(_safe_get(elem_detailing, ("width_in", "width")) or _safe_get(elem_design, ("width_in", "width")) or 60.0)
    thk = float(_safe_get(elem_detailing, ("thickness_in", "thickness")) or _safe_get(elem_design, ("thickness_in", "thickness")) or 24.0)

    is_metric = proj_l >= 500.0 or col_sp >= 1000.0

    return CombinedFootingData(
        name=f"CF{elem_id}",
        proj_left_in=proj_l if not is_metric else (proj_l if proj_l >= 500 else 750.0),
        proj_right_in=proj_r if not is_metric else (proj_r if proj_r >= 500 else 750.0),
        col_spacing_in=col_sp if not is_metric else (col_sp if col_sp >= 1000 else 3000.0),
        width_in=w if not is_metric else (w if w >= 500 else 1500.0),
        thickness_in=thk if not is_metric else (thk if thk >= 200 else 600.0),
        col1_width_in=16.0 if not is_metric else 400.0,
        col1_depth_in=16.0 if not is_metric else 400.0,
        col2_width_in=16.0 if not is_metric else 400.0,
        col2_depth_in=16.0 if not is_metric else 400.0,
    )


def _element_to_column_data(
    elem_id: Union[int, str],
    elem_detailing: Any,
    elem_design: Optional[Any],
    model: Optional[Any],
) -> ColumnData:
    """Convert struct_core detailing/design/model -> struct_draw ColumnData."""
    w, d, cover, length, is_metric = _extract_section_properties(
        elem_id, elem_detailing, elem_design, model, default_w=16.0, default_d=16.0, default_cover=1.5, default_length=144.0
    )

    bar_layout = getattr(elem_detailing, "bar_layout", None)
    bars_list: List[Rebar] = []
    tie_size = "T10" if is_metric else "#3"
    tie_spacing = 200.0 if is_metric else 12.0
    tie_obj = Stirrup(size=tie_size, spacing_in=tie_spacing, legs=2, width_in=max(1.0, w - 2 * cover), height_in=max(1.0, d - 2 * cover))

    if bar_layout:
        if hasattr(bar_layout, "top_layers") and bar_layout.top_layers:
            for layer in bar_layout.top_layers:
                for b in getattr(layer, "bars", []):
                    b_size = getattr(b, "size", 8 if not is_metric else 20)
                    b_size_str = f"#{b_size}" if not is_metric and not str(b_size).startswith("#") else (f"T{b_size}" if is_metric and not str(b_size).startswith("T") else str(b_size))
                    bars_list.append(
                        Rebar(
                            mark=getattr(b, "mark", "C1"),
                            size=b_size_str,
                            quantity=getattr(b, "count", 8),
                            length_in=getattr(b, "length", length),
                        )
                    )

        if hasattr(bar_layout, "stirrups") and bar_layout.stirrups:
            st = bar_layout.stirrups[0]
            st_sz = getattr(st, "size", 3 if not is_metric else 10)
            st_sz_str = f"#{st_sz}" if not is_metric and not str(st_sz).startswith("#") else (f"T{st_sz}" if is_metric and not str(st_sz).startswith("T") else str(st_sz))
            tie_obj = Stirrup(
                size=st_sz_str,
                spacing_in=float(getattr(st, "spacing", tie_spacing)),
                legs=int(getattr(st, "legs", 2)),
                width_in=max(1.0, w - 2.0 * cover),
                height_in=max(1.0, d - 2.0 * cover),
            )

    if not bars_list:
        bars_list = [Rebar(mark="C1", size="T20" if is_metric else "#8", quantity=8, length_in=length)]

    return ColumnData(
        name=f"C{elem_id}",
        section=GeometrySection(width_in=w, depth_in=d, cover_in=cover),
        longitudinal_bars=tuple(bars_list),
        stirrups=tie_obj,
    )


def _element_to_staircase_data(
    elem_id: Union[int, str],
    elem_detailing: Any,
    elem_design: Optional[Any],
    model: Optional[Any],
) -> StaircaseData:
    """Convert struct_core detailing/design -> struct_draw StaircaseData."""
    f_w = float(_safe_get(elem_detailing, ("flight_width_in", "flight_width", "width")) or _safe_get(elem_design, ("flight_width_in", "flight_width", "width")) or 48.0)
    riser = float(_safe_get(elem_detailing, ("riser_height_in", "riser_height", "riser")) or _safe_get(elem_design, ("riser_height_in", "riser_height", "riser")) or 6.0)
    tread = float(_safe_get(elem_detailing, ("tread_depth_in", "tread_depth", "tread")) or _safe_get(elem_design, ("tread_depth_in", "tread_depth", "tread")) or 10.0)
    n_risers = int(_safe_get(elem_detailing, ("num_risers", "steps")) or _safe_get(elem_design, ("num_risers", "steps")) or 10)
    slab_thk = float(_safe_get(elem_detailing, ("slab_thickness_in", "waist_thickness", "thickness")) or _safe_get(elem_design, ("slab_thickness_in", "waist_thickness", "thickness")) or 6.0)

    is_metric = f_w >= 500.0 or riser >= 50.0

    return StaircaseData(
        name=f"ST{elem_id}",
        flight_width_in=f_w if not is_metric else (f_w if f_w >= 500 else 1200.0),
        riser_height_in=riser if not is_metric else (riser if riser >= 50 else 150.0),
        tread_depth_in=tread if not is_metric else (tread if tread >= 100 else 250.0),
        num_risers=n_risers,
        slab_thickness_in=slab_thk if not is_metric else (slab_thk if slab_thk >= 50 else 150.0),
    )


def _element_to_slab_data(
    elem_id: Union[int, str],
    elem_detailing: Any,
    elem_design: Optional[Any],
    model: Optional[Any],
) -> SlabData:
    """Convert struct_core detailing/design -> struct_draw SlabData."""
    length = float(_safe_get(elem_detailing, ("length_in", "length", "lx")) or _safe_get(elem_design, ("length_in", "length", "lx")) or 240.0)
    width = float(_safe_get(elem_detailing, ("width_in", "width", "ly")) or _safe_get(elem_design, ("width_in", "width", "ly")) or 180.0)
    thk = float(_safe_get(elem_detailing, ("thickness_in", "thickness", "h")) or _safe_get(elem_design, ("thickness_in", "thickness", "h")) or 6.0)
    cover = float(_safe_get(elem_detailing, ("cover_in", "cover")) or _safe_get(elem_design, ("cover_in", "cover")) or 0.75)

    is_metric = length >= 1000.0 or width >= 1000.0 or thk >= 50.0

    t_bar = Rebar(mark="T1", size="T10" if is_metric else "#4", quantity=10)
    b_bar = Rebar(mark="B1", size="T12" if is_metric else "#5", quantity=12)

    return SlabData(
        name=f"SL{elem_id}",
        length_in=length if not is_metric else (length if length >= 1000 else 6000.0),
        width_in=width if not is_metric else (width if width >= 1000 else 4500.0),
        thickness_in=thk if not is_metric else (thk if thk >= 50 else 150.0),
        cover_in=cover if not is_metric else (cover if cover >= 10 else 20.0),
        top_bar=t_bar,
        bottom_bar=b_bar,
    )


# ---------------------------------------------------------------------------
# General Framing / Arrangement extractor
# ---------------------------------------------------------------------------


def _model_to_general_frame_data(
    model: Any,
    *,
    view_mode: str = "both",
    title: Optional[str] = None,
) -> GeneralFrameData:
    """Convert a structural model's nodes, elements, grids, and levels into GeneralFrameData."""
    nodes_list: List[FrameNode] = []
    members_list: List[FrameMember] = []
    grid_x_list: List[FrameGridLine] = []
    grid_y_list: List[FrameGridLine] = []
    levels_list: List[FrameLevelLine] = []

    is_metric = False

    # Extract nodes
    nodes = getattr(model, "nodes", None)
    if isinstance(nodes, dict):
        for n_id, n_obj in nodes.items():
            nx = float(getattr(n_obj, "x", 0.0))
            ny = float(getattr(n_obj, "y", 0.0))
            nz = float(getattr(n_obj, "z", 0.0))
            if nx >= 1000.0 or ny >= 1000.0 or nz >= 1000.0:
                is_metric = True
            # For 2D elevation, Y coordinate is typically elevation (or Z in 3D)
            elev = nz if nz != 0.0 else ny
            nodes_list.append(FrameNode(id=n_id, x=nx, y=elev, z=nz))
    elif isinstance(nodes, (list, tuple)):
        for idx, n_obj in enumerate(nodes):
            n_id = getattr(n_obj, "id", idx + 1)
            nx = float(getattr(n_obj, "x", 0.0))
            ny = float(getattr(n_obj, "y", 0.0))
            nz = float(getattr(n_obj, "z", 0.0))
            if nx >= 1000.0 or ny >= 1000.0 or nz >= 1000.0:
                is_metric = True
            elev = nz if nz != 0.0 else ny
            nodes_list.append(FrameNode(id=n_id, x=nx, y=elev, z=nz))

    # Extract members
    elements = getattr(model, "elements", None) or getattr(model, "members", None)
    if isinstance(elements, dict):
        for e_id, e_obj in elements.items():
            members_list.append(_create_frame_member(e_id, e_obj, model, is_metric))
    elif isinstance(elements, (list, tuple)):
        for idx, e_obj in enumerate(elements):
            e_id = getattr(e_obj, "id", f"M{idx+1}")
            members_list.append(_create_frame_member(e_id, e_obj, model, is_metric))

    # Extract grid lines
    grids = getattr(model, "grids", None) or getattr(model, "grid_lines", None)
    if isinstance(grids, dict):
        for g_lbl, g_val in grids.items():
            axis = "X" if str(g_lbl).isalpha() else "Y"
            grid_x_list.append(FrameGridLine(label=str(g_lbl), coord=float(g_val), axis=axis))
    elif isinstance(grids, (list, tuple)):
        for g_obj in grids:
            grid_x_list.append(
                FrameGridLine(
                    label=str(getattr(g_obj, "label", "A")),
                    coord=float(getattr(g_obj, "coord", 0.0)),
                    axis=getattr(g_obj, "axis", "X"),
                )
            )

    # Extract levels
    levels = getattr(model, "levels", None) or getattr(model, "stories", None)
    if isinstance(levels, dict):
        for l_lbl, l_val in levels.items():
            levels_list.append(FrameLevelLine(label=str(l_lbl), elevation=float(l_val)))
    elif isinstance(levels, (list, tuple)):
        for l_obj in levels:
            levels_list.append(
                FrameLevelLine(
                    label=str(getattr(l_obj, "label", "GL")),
                    elevation=float(getattr(l_obj, "elevation", 0.0)),
                )
            )

    # If no elements were found, build a representative default frame
    if not nodes_list or not members_list:
        return GeneralFrameData.from_grid(
            name="MODEL-FRAME",
            bays=(6000.0, 6000.0, 6000.0) if is_metric else (240.0, 240.0, 240.0),
            story_heights=(4000.0, 3500.0, 3500.0) if is_metric else (144.0, 120.0, 120.0),
            col_width=400.0 if is_metric else 16.0,
            col_depth=400.0 if is_metric else 16.0,
            beam_width=300.0 if is_metric else 12.0,
            beam_depth=500.0 if is_metric else 20.0,
            title=title or "BUILDING GENERAL FRAMING ELEVATION",
            is_metric=is_metric,
        )

    return GeneralFrameData(
        name=getattr(model, "name", "MODEL-FRAME"),
        nodes=tuple(nodes_list),
        members=tuple(members_list),
        grid_x=tuple(grid_x_list),
        grid_y=tuple(grid_y_list),
        levels=tuple(levels_list),
        title=title or "GENERAL FRAMING ELEVATION & PLAN",
        view_mode=view_mode,
        is_metric=is_metric,
    )


def _create_frame_member(e_id: Any, e_obj: Any, model: Any, is_metric: bool) -> FrameMember:
    """Helper to convert a model element into a FrameMember."""
    s_node = getattr(e_obj, "start_node", getattr(e_obj, "node_i", 1))
    e_node = getattr(e_obj, "end_node", getattr(e_obj, "node_j", 2))
    m_type = str(getattr(e_obj, "member_type", "beam")).lower()
    name = str(getattr(e_obj, "name", f"{m_type[0].upper()}{e_id}"))

    w = float(_safe_get(e_obj, ("width_in", "width", "b", "bw")) or (300.0 if is_metric else 12.0))
    d = float(_safe_get(e_obj, ("depth_in", "depth", "h", "height")) or (500.0 if is_metric else 18.0))

    return FrameMember(
        id=e_id,
        start_node=s_node,
        end_node=e_node,
        member_type=m_type,
        name=name,
        section_name=f"{int(w)}x{int(d)}",
        width_in=w,
        depth_in=d,
    )


__all__ = [
    "draw_from_core",
    "draw_general_frame_from_core",
]

