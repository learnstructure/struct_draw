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
from pathlib import Path
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
from struct_draw.core.units import (
    DrawingScale,
    DrawingUnit,
    SCALE_1_100,
    SCALE_1_50,
    SCALE_1_20,
    SCALE_1_4_IN,
    SCALE_1_8_IN,
    SCALE_1_IN,
    drawing_unit_from_core,
)
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
    scale: Optional[Union[str, DrawingScale]] = None,
    unit: Optional[Union[str, DrawingUnit]] = None,
    plan_scale: Optional[Union[str, DrawingScale]] = None,
    elev_scale: Optional[Union[str, DrawingScale]] = None,
    detail_scale: Optional[Union[str, DrawingScale]] = None,
    view_mode: str = "both",
    story_level: Optional[Union[str, int, float]] = None,
    grid_line: Optional[Union[str, float]] = None,
) -> Dict[str, Any]:
    """
    Render struct_core results into DXF drawings with full unit and scale awareness.

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
    scale : str or DrawingScale, optional
        Global drawing scale (e.g. "1:50", "1/4\"=1'-0\"").
    unit : str or DrawingUnit, optional
        Drawing unit system (e.g. DrawingUnit.MM, DrawingUnit.IN, "mm", "in").
    plan_scale : str or DrawingScale, optional
        Scale specifically for framing plan views (default: 1:100 metric or 1/8"=1'-0" imperial).
    elev_scale : str or DrawingScale, optional
        Scale specifically for frame elevation views (default: 1:50 metric or 1/4"=1'-0" imperial).
    detail_scale : str or DrawingScale, optional
        Scale specifically for member cross-sections & details (default: 1:20 metric or 1"=1'-0" imperial).
    view_mode : str, optional
        For composite drawings: "both" (plan + elevations), "plan" (floor framing plan only),
        or "elevation" (frame elevations only). Default is "both".
    story_level : str, int, or float, optional
        Story level filter for framing plan view.
    grid_line : str or float, optional
        Grid line filter for frame elevation view.

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
    project = None

    if isinstance(detailing_or_project, Project):
        project = detailing_or_project
        detailing_res = getattr(project, "detailing_result", None)
        if detailing_res is None and getattr(project, "detailing_results", None):
            detailing_res = next(iter(project.detailing_results.values()))
        if design_result is None:
            design_result = getattr(project, "design_result", None)
            if design_result is None and getattr(project, "design_results", None):
                design_result = next(iter(project.design_results.values()))
        if model_or_project is None:
            model = getattr(project, "model", None)
    elif isinstance(detailing_or_project, StructuralModel):
        model = detailing_or_project
    else:
        detailing_res = detailing_or_project

    if model_or_project is not None:
        if isinstance(model_or_project, Project):
            if project is None:
                project = model_or_project
            if model is None:
                model = model_or_project.model
        elif model is None:
            model = model_or_project

    # Resolve unit
    if unit is not None:
        d_unit = DrawingUnit.from_str(str(unit))
    elif project is not None or model is not None:
        d_unit, _, _ = drawing_unit_from_core(project if project is not None else model)
    else:
        is_m = _detect_is_metric(detailing_res, model, project)
        d_unit = DrawingUnit.MM if is_m else DrawingUnit.IN

    is_metric = d_unit.is_metric

    # Resolve scales
    if scale is not None:
        d_scale = DrawingScale.from_str(str(scale), is_metric=is_metric) if isinstance(scale, str) else scale
        p_scale = DrawingScale.from_str(str(plan_scale), is_metric=is_metric) if isinstance(plan_scale, str) else (plan_scale or d_scale)
        e_scale = DrawingScale.from_str(str(elev_scale), is_metric=is_metric) if isinstance(elev_scale, str) else (elev_scale or d_scale)
        det_scale = DrawingScale.from_str(str(detail_scale), is_metric=is_metric) if isinstance(detail_scale, str) else (detail_scale or d_scale)
    else:
        if is_metric:
            p_scale = DrawingScale.from_str(str(plan_scale), is_metric=True) if isinstance(plan_scale, str) else (plan_scale or SCALE_1_100)
            e_scale = DrawingScale.from_str(str(elev_scale), is_metric=True) if isinstance(elev_scale, str) else (elev_scale or SCALE_1_50)
            det_scale = DrawingScale.from_str(str(detail_scale), is_metric=True) if isinstance(detail_scale, str) else (detail_scale or SCALE_1_20)
        else:
            p_scale = DrawingScale.from_str(str(plan_scale), is_metric=False) if isinstance(plan_scale, str) else (plan_scale or SCALE_1_8_IN)
            e_scale = DrawingScale.from_str(str(elev_scale), is_metric=False) if isinstance(elev_scale, str) else (elev_scale or SCALE_1_4_IN)
            det_scale = DrawingScale.from_str(str(detail_scale), is_metric=False) if isinstance(detail_scale, str) else (detail_scale or SCALE_1_IN)

    # If general framing requested or no detailing is present but a model exists, generate GA framing drawing
    if view_type in ("general_frame", "plan", "elevation") or (detailing_res is None or not getattr(detailing_res, "element_results", None)):
        if model is not None:
            v_mode = "plan" if view_type == "plan" else ("elevation" if view_type == "elevation" else "both")
            return draw_general_frame_from_core(
                project or model,
                view_mode=v_mode,
                scale=scale,
                unit=d_unit,
                plan_scale=p_scale,
                elev_scale=e_scale,
            )
        doc = _new_doc(is_metric=is_metric, unit=d_unit, scale=det_scale)
        return {"drawing": doc, "data": {}, "elements_drawn": 0}

    doc = _new_doc(is_metric=is_metric, unit=d_unit, scale=det_scale)
    msp = doc.modelspace()

    member_data_map: Dict[Union[int, str], Any] = {}
    x_offset = 0.0
    elements_drawn = 0
    y_detailing = 0.0

    if model is not None and view_type in ("auto", "all"):
        v_mode = str(view_mode or "both").lower()
        # Determine whether model is 3D
        raw_nodes = getattr(model, "nodes", None) or []
        nl = list(raw_nodes.values()) if isinstance(raw_nodes, dict) else list(raw_nodes)
        is_3d = False
        if nl:
            z_vals = [float(getattr(n, "z", 0.0) or 0.0) for n in nl]
            is_3d = (max(z_vals) - min(z_vals)) > 1e-3

        lowest_y = 0.0
        plan_bbox = None
        elev1_bbox = None
        margin = 3500.0 if is_metric else 140.0

        if v_mode in ("both", "plan"):
            plan_data = create_general_frame_data_from_model(
                project or model,
                view_mode="plan",
                story_level=story_level,
                scale=p_scale,
                unit=d_unit,
            )
            res_plan = general_frame.plan_view(msp, plan_data, origin=(0.0, 0.0), scale=p_scale, unit=d_unit)
            plan_bbox = res_plan.get("bounding_box", (0.0, 0.0, 500.0, 500.0))
            lowest_y = min(lowest_y, plan_bbox[1])
            member_data_map["plan"] = plan_data

        if v_mode in ("both", "elevation"):
            elev_data = create_general_frame_data_from_model(
                project or model,
                view_mode="elevation",
                grid_line=grid_line,
                scale=e_scale,
                unit=d_unit,
            )
            if elev_data.levels:
                elev_h = max(l.elevation for l in elev_data.levels) - min(l.elevation for l in elev_data.levels)
            elif elev_data.nodes:
                elev_h = max(n.y for n in elev_data.nodes) - min(n.y for n in elev_data.nodes)
            else:
                elev_h = 10000.0 if is_metric else 360.0

            top_headroom = 1500.0 if is_metric else 60.0
            elev_y = (plan_bbox[1] - margin - elev_h - top_headroom) if plan_bbox else 0.0
            res_elev1 = general_frame.elevation_view(msp, elev_data, origin=(0.0, elev_y), scale=e_scale, unit=d_unit)
            elev1_bbox = res_elev1.get("bounding_box", (0.0, elev_y, 5000.0, elev_y + elev_h))
            lowest_y = min(lowest_y, elev1_bbox[1])
            member_data_map["elevation"] = elev_data

            # Transverse elevation for 3D models with both X and Y grids
            if is_3d and (not grid_line) and bool(getattr(elev_data, "grid_x", None)) and bool(getattr(elev_data, "grid_y", None)) and len(elev_data.grid_x) > 0 and len(elev_data.grid_y) > 0:
                elev_data_2 = create_general_frame_data_from_model(
                    project or model,
                    view_mode="elevation",
                    view_axis="X",
                    scale=e_scale,
                    unit=d_unit,
                )
                elev2_x = elev1_bbox[2] + margin
                res_elev2 = general_frame.elevation_view(msp, elev_data_2, origin=(elev2_x, elev_y), scale=e_scale, unit=d_unit)
                elev2_bbox = res_elev2.get("bounding_box", (elev2_x, elev_y, elev2_x + 5000.0, elev_y + elev_h))
                lowest_y = min(lowest_y, elev2_bbox[1])
                member_data_map["elevation_transverse"] = elev_data_2

        y_detailing = lowest_y - margin

    elem_results = getattr(detailing_res, "element_results", {})
    des_results = getattr(design_result, "element_results", {}) if design_result else {}

    # Pre-calculate detailing baseline so tall members (columns) and sections align cleanly
    max_col_h = 0.0
    for e_id, e_det in elem_results.items():
        e_des = des_results.get(e_id) if des_results else None
        m_type = _determine_member_type(e_det, e_des, model, e_id)
        if m_type == "column":
            _, _, _, col_len, is_m = _extract_section_properties(e_id, e_det, e_des, model, project=project, default_length=144.0)
            max_col_h = max(max_col_h, col_len)

    if max_col_h > 0:
        h_b = min(max_col_h * 0.2, 600.0 if is_metric else 24.0)
        h_s = min(max_col_h * 0.25, 450.0 if is_metric else 18.0)
        top_headroom = h_b + h_s + (600.0 if is_metric else 24.0)
        detailing_baseline_y = y_detailing - (max_col_h + top_headroom)
    else:
        detailing_baseline_y = y_detailing

    for elem_id, elem_detailing in elem_results.items():
        elem_design = des_results.get(elem_id) if des_results else None

        member_type = _determine_member_type(elem_detailing, elem_design, model, elem_id)

        if member_type == "beam":
            beam_data = _element_to_beam_data(
                elem_id, elem_detailing, elem_design, model, project=project, scale=det_scale, unit=d_unit
            )
            y_beam = (detailing_baseline_y + (max_col_h - beam_data.section.depth_in) / 2.0) if max_col_h > 0 else detailing_baseline_y
            beam.section_view(
                msp, beam_data, origin=(x_offset, y_beam), title=f"SECTION {beam_data.name}", scale=det_scale, unit=d_unit
            )
            member_data_map[elem_id] = beam_data
            step = max(beam_data.section.width_in + (1200.0 if beam_data.is_metric else 48.0), 2000.0 if beam_data.is_metric else 80.0)
            x_offset += step
            elements_drawn += 1

        elif member_type == "beam_profile":
            prof_data = _element_to_beam_profile_data(
                elem_id, elem_detailing, elem_design, model, project=project, scale=det_scale, unit=d_unit
            )
            beam_profile.drawing(msp, prof_data, origin=(x_offset, detailing_baseline_y), scale=det_scale, unit=d_unit)
            member_data_map[elem_id] = prof_data
            step = sum(prof_data.spans_in) + (1500.0 if prof_data.is_metric else 60.0)
            x_offset += step
            elements_drawn += 1

        elif member_type == "column":
            col_data = _element_to_column_data(
                elem_id, elem_detailing, elem_design, model, project=project, scale=det_scale, unit=d_unit
            )
            res_col = column.drawing(
                msp, col_data, origin=(x_offset, detailing_baseline_y), title=f"COLUMN {col_data.name}", scale=det_scale, unit=d_unit
            )
            member_data_map[elem_id] = col_data
            col_bbox = res_col.get("bounding_box", (x_offset, detailing_baseline_y, x_offset + 100.0, detailing_baseline_y + col_data.height_in))
            step = (col_bbox[2] - col_bbox[0]) + (800.0 if col_data.is_metric else 40.0)
            x_offset += step
            elements_drawn += 1

        elif member_type == "footing":
            ftg_data = _element_to_footing_data(
                elem_id, elem_detailing, elem_design, model, project=project, scale=det_scale, unit=d_unit
            )
            footing.section_view(msp, ftg_data, origin=(x_offset, y_detailing), scale=det_scale, unit=d_unit)
            f_margin = 800.0 if ftg_data.is_metric else 35.0
            y_plan = y_detailing - (ftg_data.footing_depth_in + ftg_data.plinth_height_in + ftg_data.width_in / 2.0 + f_margin)
            footing.plan_view(msp, ftg_data, origin=(x_offset, y_plan), scale=det_scale, unit=d_unit)
            member_data_map[elem_id] = ftg_data
            step = ftg_data.length_in + (1000.0 if ftg_data.is_metric else 40.0)
            x_offset += step
            elements_drawn += 1

        elif member_type == "combined_footing":
            cf_data = _element_to_combined_footing_data(
                elem_id, elem_detailing, elem_design, model, project=project, scale=det_scale, unit=d_unit
            )
            combined_footing.section_view(msp, cf_data, origin=(x_offset, y_detailing), scale=det_scale, unit=d_unit)
            cf_margin = 800.0 if cf_data.is_metric else 35.0
            y_plan = y_detailing - (cf_data.footing_depth_in + cf_data.plinth_height_in + cf_data.width_in / 2.0 + cf_margin)
            combined_footing.plan_view(msp, cf_data, origin=(x_offset, y_plan), scale=det_scale, unit=d_unit)
            member_data_map[elem_id] = cf_data
            step = cf_data.total_length_in + (1000.0 if cf_data.is_metric else 40.0)
            x_offset += step
            elements_drawn += 1

        elif member_type == "staircase":
            st_data = _element_to_staircase_data(
                elem_id, elem_detailing, elem_design, model, project=project, scale=det_scale, unit=d_unit
            )
            staircase.section_view(msp, st_data, origin=(x_offset, y_detailing), scale=det_scale, unit=d_unit)
            st_margin = 1500.0 if st_data.is_metric else 60.0
            y_plan = y_detailing - (st_data.flight_width_in * 2.5 + st_margin)
            staircase.plan_view(msp, st_data, origin=(x_offset, y_plan), scale=det_scale, unit=d_unit)
            member_data_map[elem_id] = st_data
            step = st_data.flight_length_in + st_data.bottom_landing_depth_in + st_data.top_landing_depth_in + (1200.0 if st_data.is_metric else 50.0)
            x_offset += step
            elements_drawn += 1

        elif member_type == "slab":
            slab_data = _element_to_slab_data(
                elem_id, elem_detailing, elem_design, model, project=project, scale=det_scale, unit=d_unit
            )
            slab.plan_view(msp, slab_data, origin=(x_offset, y_detailing), scale=det_scale, unit=d_unit)
            sl_margin = 1000.0 if slab_data.is_metric else 50.0
            y_sec = y_detailing - (slab_data.width_in + sl_margin)
            slab.section_view(msp, slab_data, origin=(x_offset, y_sec), scale=det_scale, unit=d_unit)
            member_data_map[elem_id] = slab_data
            step = slab_data.length_in + (1200.0 if slab_data.is_metric else 50.0)
            x_offset += step
            elements_drawn += 1

    # Master Project Bar Bending Schedule
    agg_sched = getattr(detailing_res, "aggregate_schedule", None)
    if agg_sched and getattr(agg_sched, "items", None):
        from struct_draw.core.composite import draw_schedule_table
        from struct_draw.core.data import ScheduleRow, ScheduleTableData

        proj_rows = []
        for it in agg_sched.items:
            b_sz = getattr(it, "bar_size", getattr(it, "size", 8))
            b_sz_str = f"#{b_sz}" if not is_metric and not str(b_sz).startswith("#") else (f"T{b_sz}" if is_metric and not str(b_sz).startswith("T") else str(b_sz))
            proj_rows.append(
                ScheduleRow(
                    mark=str(getattr(it, "mark", "")),
                    size=b_sz_str,
                    quantity=int(getattr(it, "quantity", 1)),
                    length_in=float(getattr(it, "cut_length", 0.0)),
                    remarks=str(getattr(it, "location", "") or getattr(it, "shape_code", "")),
                    shape_code=str(getattr(it, "shape_code", "")),
                    total_weight=float(getattr(it, "weight", 0.0) or 0.0),
                )
            )

        proj_table = ScheduleTableData(
            title="PROJECT BAR BENDING SCHEDULE",
            rows=tuple(proj_rows),
            unit="mm" if is_metric else "in",
            scale=det_scale,
            total_weight=float(getattr(agg_sched, "total_weight", 0.0) or 0.0),
        )

        table_margin = 1500.0 if is_metric else 60.0
        table_y = detailing_baseline_y - table_margin
        draw_schedule_table(
            msp,
            proj_table,
            origin=(0.0, table_y),
            align="left",
            scale=det_scale,
            unit=d_unit,
        )
        member_data_map["project_schedule"] = proj_table

    has_framing = "plan" in member_data_map or "elevation" in member_data_map
    return {
        "drawing": doc,
        "data": member_data_map,
        "elements_drawn": elements_drawn,
        "has_framing": has_framing,
    }


def draw_general_frame_from_core(
    model_or_project: Union[StructuralModel, Project, Any],
    *,
    view_mode: str = "both",  # "elevation", "plan", "both"
    story_level: Optional[Union[str, int, float]] = None,
    grid_line: Optional[Union[str, float]] = None,
    view_axis: Optional[str] = None,
    title: Optional[str] = None,
    scale: Optional[Union[str, DrawingScale]] = None,
    unit: Optional[Union[str, DrawingUnit]] = None,
    plan_scale: Optional[Union[str, DrawingScale]] = None,
    elev_scale: Optional[Union[str, DrawingScale]] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """
    Generate General Arrangement / Framing Drawings (plan and/or elevation outlines of beams, columns, trusses)
    directly from a structural model without rebar details.
    """
    project = model_or_project if isinstance(model_or_project, Project) else None
    model = getattr(model_or_project, "model", model_or_project)

    if unit is not None:
        d_unit = DrawingUnit.from_str(str(unit))
    elif project is not None or model is not None:
        d_unit, _, _ = drawing_unit_from_core(project if project is not None else model)
    else:
        d_unit = DrawingUnit.MM

    is_metric = d_unit.is_metric

    if scale is not None:
        d_scale = DrawingScale.from_str(str(scale), is_metric=is_metric) if isinstance(scale, str) else scale
        p_scale = DrawingScale.from_str(str(plan_scale), is_metric=is_metric) if isinstance(plan_scale, str) else (plan_scale or d_scale)
        e_scale = DrawingScale.from_str(str(elev_scale), is_metric=is_metric) if isinstance(elev_scale, str) else (elev_scale or d_scale)
    else:
        if is_metric:
            p_scale = DrawingScale.from_str(str(plan_scale), is_metric=True) if isinstance(plan_scale, str) else (plan_scale or SCALE_1_100)
            e_scale = DrawingScale.from_str(str(elev_scale), is_metric=True) if isinstance(elev_scale, str) else (elev_scale or SCALE_1_50)
        else:
            p_scale = DrawingScale.from_str(str(plan_scale), is_metric=False) if isinstance(plan_scale, str) else (plan_scale or SCALE_1_8_IN)
            e_scale = DrawingScale.from_str(str(elev_scale), is_metric=False) if isinstance(elev_scale, str) else (elev_scale or SCALE_1_4_IN)

    if view_mode == "both":
        plan_data = create_general_frame_data_from_model(
            model_or_project,
            view_mode="plan",
            story_level=story_level,
            title=title,
            scale=p_scale,
            unit=d_unit,
        )
        elev_data = create_general_frame_data_from_model(
            model_or_project,
            view_mode="elevation",
            grid_line=grid_line,
            view_axis=view_axis,
            title=title,
            scale=e_scale,
            unit=d_unit,
        )

        doc = _new_doc(is_metric=is_metric, unit=d_unit, scale=p_scale)
        msp = doc.modelspace()

        res_plan = general_frame.plan_view(msp, plan_data, origin=(0.0, 0.0), scale=p_scale, unit=d_unit)
        plan_bbox = res_plan.get("bounding_box", (0.0, 0.0, 500.0, 500.0))
        margin = 3500.0 if is_metric else 140.0

        if elev_data.levels:
            elev_h = max(l.elevation for l in elev_data.levels) - min(l.elevation for l in elev_data.levels)
        elif elev_data.nodes:
            elev_h = max(n.y for n in elev_data.nodes) - min(n.y for n in elev_data.nodes)
        else:
            elev_h = 10000.0 if is_metric else 360.0

        top_headroom = 1500.0 if is_metric else 60.0
        elev_y = plan_bbox[1] - margin - elev_h - top_headroom
        res_elev = general_frame.elevation_view(msp, elev_data, origin=(0.0, elev_y), scale=e_scale, unit=d_unit)
        elev_bbox = res_elev.get("bounding_box", (0.0, elev_y, 5000.0, elev_y + elev_h))

        # Check if 3D model with grids in both orthogonal directions (and grid_line was not explicitly specified)
        res_elev2 = None
        elev_data_2 = None
        has_transverse = (
            grid_line is None
            and bool(plan_data.grid_x)
            and bool(plan_data.grid_y)
            and len(plan_data.grid_x) > 0
            and len(plan_data.grid_y) > 0
        )
        if has_transverse:
            elev_data_2 = create_general_frame_data_from_model(
                model_or_project,
                view_mode="elevation",
                view_axis="X",
                title=title,
                scale=e_scale,
                unit=d_unit,
            )
            elev2_x = elev_bbox[2] + margin
            res_elev2 = general_frame.elevation_view(msp, elev_data_2, origin=(elev2_x, elev_y), scale=e_scale, unit=d_unit)

        if output_path is not None:
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            doc.saveas(str(out_p))

        raw_elems = getattr(model, "elements", None) or getattr(model, "members", None) or ()
        n_elems = len(raw_elems) if raw_elems else len(elev_data.members)

        ret_data = {"plan": plan_data, "elevation": elev_data, "frame": elev_data}
        ret_views = {"plan": res_plan, "elevation": res_elev}
        if elev_data_2 is not None and res_elev2 is not None:
            ret_data["elevation_transverse"] = elev_data_2
            ret_data["elevation_y"] = elev_data_2
            ret_views["elevation_transverse"] = res_elev2
            ret_views["elevation_x"] = res_elev
            ret_views["elevation_y"] = res_elev2

        return {
            "drawing": doc,
            "data": ret_data,
            "elements_drawn": n_elems,
            "views": ret_views,
        }

    elif view_mode == "plan":
        frame_data = create_general_frame_data_from_model(
            model_or_project,
            view_mode="plan",
            story_level=story_level,
            title=title,
            scale=p_scale,
            unit=d_unit,
        )
        doc = _new_doc(is_metric=is_metric, unit=d_unit, scale=p_scale)
        msp = doc.modelspace()
        res = general_frame.plan_view(msp, frame_data, origin=(0.0, 0.0), scale=p_scale, unit=d_unit)

        if output_path is not None:
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            doc.saveas(str(out_p))

        raw_elems = getattr(model, "elements", None) or getattr(model, "members", None) or ()
        n_elems = len(raw_elems) if raw_elems else len(frame_data.members)

        return {
            "drawing": doc,
            "data": {"plan": frame_data, "frame": frame_data},
            "elements_drawn": n_elems,
            "views": {"plan": res},
        }

    else:
        # Elevation
        frame_data = create_general_frame_data_from_model(
            model_or_project,
            view_mode="elevation",
            grid_line=grid_line,
            view_axis=view_axis,
            title=title,
            scale=e_scale,
            unit=d_unit,
        )
        doc = _new_doc(is_metric=is_metric, unit=d_unit, scale=e_scale)
        msp = doc.modelspace()
        res = general_frame.elevation_view(msp, frame_data, origin=(0.0, 0.0), scale=e_scale, unit=d_unit)

        if output_path is not None:
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            doc.saveas(str(out_p))

        raw_elems = getattr(model, "elements", None) or getattr(model, "members", None) or ()
        n_elems = len(raw_elems) if raw_elems else len(frame_data.members)

        return {
            "drawing": doc,
            "data": {"elevation": frame_data, "frame": frame_data},
            "elements_drawn": n_elems,
            "views": {"elevation": res},
        }



def draw_framing_plan_from_core(
    model_or_project: Union[StructuralModel, Project, Any],
    *,
    story_level: Optional[Union[str, int, float]] = None,
    title: Optional[str] = None,
    scale: Optional[Union[str, DrawingScale]] = None,
    unit: Optional[Union[str, DrawingUnit]] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Generate a floor or roof framing plan view from a structural model."""
    return draw_general_frame_from_core(
        model_or_project,
        view_mode="plan",
        story_level=story_level,
        title=title,
        scale=scale,
        unit=unit,
        output_path=output_path,
    )


def draw_frame_elevation_from_core(
    model_or_project: Union[StructuralModel, Project, Any],
    *,
    grid_line: Optional[Union[str, float]] = None,
    view_axis: Optional[str] = None,
    title: Optional[str] = None,
    scale: Optional[Union[str, DrawingScale]] = None,
    unit: Optional[Union[str, DrawingUnit]] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Generate a 2D frame elevation along a grid line from a structural model."""
    return draw_general_frame_from_core(
        model_or_project,
        view_mode="elevation",
        grid_line=grid_line,
        view_axis=view_axis,
        title=title,
        scale=scale,
        unit=unit,
        output_path=output_path,
    )


def _new_doc(
    is_metric: bool = False,
    unit: Optional[Union[str, DrawingUnit]] = None,
    scale: Optional[Union[str, DrawingScale]] = None,
) -> Any:
    """Create a fully-styled DXF document matching struct_draw.backends."""
    if unit is not None:
        d_unit = DrawingUnit.from_str(unit)
    else:
        d_unit = DrawingUnit.MM if is_metric else DrawingUnit.IN
    if scale is not None:
        d_scale = DrawingScale.from_str(scale, is_metric=d_unit.is_metric)
    else:
        d_scale = None
    doc = new_drawing()
    register_all_styles(
        doc,
        layers=default_layers(),
        linetypes=default_linetypes(),
        text_styles=default_text_styles(),
        dimension_styles=default_dimension_styles(is_metric=d_unit.is_metric, scale=d_scale, unit=d_unit),
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
    project: Optional[Any] = None,
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
        length = _safe_get(elem_detailing, ("length_in", "length", "span", "span_in", "flight_length_in", "height", "height_in", "col_height", "column_height"))

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
            length = _safe_get(elem_design, ("length_in", "length", "span", "height", "height_in", "col_height", "column_height"))

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
            if length is None:
                length = getattr(elem_obj, "length", None)
            # Check length from nodes
            start_node_id = getattr(elem_obj, "start_node", getattr(elem_obj, "node_i", None))
            end_node_id = getattr(elem_obj, "end_node", getattr(elem_obj, "node_j", None))
            nodes = getattr(model, "nodes", None)
            if (length is None or length <= 0) and start_node_id is not None and end_node_id is not None:
                n1, n2 = None, None
                if isinstance(nodes, dict):
                    n1 = nodes.get(start_node_id)
                    n2 = nodes.get(end_node_id)
                elif isinstance(nodes, (list, tuple)):
                    for n in nodes:
                        n_id = getattr(n, "id", None)
                        if n_id == start_node_id:
                            n1 = n
                        if n_id == end_node_id:
                            n2 = n
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

    # Determine metric context
    has_explicit_metric = None
    if project is not None and getattr(project, "metadata", None) is not None:
        meta_units = getattr(project.metadata, "units", None)
        if meta_units is not None:
            u_sys = str(getattr(meta_units, "system", "")).lower()
            u_len = str(getattr(meta_units, "length", "")).lower()
            if u_sys in ("metric", "si") or u_len in ("m", "meter", "meters", "mm", "cm"):
                has_explicit_metric = True
            elif u_sys in ("imperial", "us_customary") or u_len in ("in", "inch", "ft", "foot", "feet"):
                has_explicit_metric = False
    if has_explicit_metric is None and model is not None:
        if hasattr(model, "is_metric"):
            has_explicit_metric = bool(model.is_metric)
        elif hasattr(model, "unit_system"):
            has_explicit_metric = "si" in str(model.unit_system).lower() or "metric" in str(model.unit_system).lower()

    test_w = float(w) if w is not None else default_w
    test_d = float(d) if d is not None else default_d
    test_len = float(length) if length is not None else default_length

    if has_explicit_metric is not None:
        is_metric = has_explicit_metric
    else:
        is_metric = test_w >= 100.0 or test_d >= 100.0 or test_len >= 1000.0

    if is_metric:
        raw_w = float(w) if w is not None else (default_w * 25.4 if default_w < 50 else default_w)
        final_w = raw_w * 1000.0 if raw_w <= 2.5 else raw_w
        raw_d = float(d) if d is not None else (default_d * 25.4 if default_d < 50 else default_d)
        final_d = raw_d * 1000.0 if raw_d <= 2.5 else raw_d
        raw_cover = float(cover) if cover is not None else (default_cover * 25.4 if default_cover < 10 else 40.0)
        final_cover = raw_cover * 1000.0 if raw_cover <= 0.2 else raw_cover
        raw_len = float(length) if length is not None else (default_length * 25.4 if default_length < 200 else default_length)
        final_len = raw_len * 1000.0 if raw_len <= 150.0 else raw_len
    else:
        final_w = float(w) if w is not None else default_w
        final_d = float(d) if d is not None else default_d
        final_cover = float(cover) if cover is not None else default_cover
        final_len = float(length) if length is not None else default_length

    return final_w, final_d, final_cover, final_len, is_metric


def _detect_is_metric(detailing_res: Any, model: Any, project: Optional[Any] = None) -> bool:
    """Check if the global project/results use metric (SI mm) units."""
    if project is not None and getattr(project, "metadata", None) is not None:
        meta_units = getattr(project.metadata, "units", None)
        if meta_units is not None:
            u_sys = str(getattr(meta_units, "system", "")).lower()
            u_len = str(getattr(meta_units, "length", "")).lower()
            if u_sys in ("metric", "si") or u_len in ("m", "meter", "meters", "mm", "cm"):
                return True
            if u_sys in ("imperial", "us_customary") or u_len in ("in", "inch", "ft", "foot", "feet"):
                return False
    if hasattr(detailing_res, "is_metric"):
        return bool(detailing_res.is_metric)
    if hasattr(model, "is_metric"):
        return bool(model.is_metric)
    if hasattr(model, "unit_system"):
        return "si" in str(model.unit_system).lower() or "metric" in str(model.unit_system).lower()

    # Check first element result
    if detailing_res and hasattr(detailing_res, "element_results") and detailing_res.element_results:
        first_elem = next(iter(detailing_res.element_results.values()))
        w, d, _, _, is_m = _extract_section_properties(0, first_elem, None, model, project=project)
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
    *,
    project: Optional[Any] = None,
    scale: Any = None,
    unit: Any = None,
) -> BeamData:
    """Convert struct_core detailing/design/model -> struct_draw BeamData."""
    w, d, cover, length, is_metric = _extract_section_properties(
        elem_id, elem_detailing, elem_design, model, project=project, default_w=12.0, default_d=18.0, default_cover=1.5
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

    elem_obj = None
    if model is not None and hasattr(model, "elements"):
        elems = getattr(model, "elements", [])
        if isinstance(elems, dict):
            elem_obj = elems.get(elem_id)
        elif isinstance(elems, (list, tuple)):
            for e in elems:
                if getattr(e, "id", None) == elem_id:
                    elem_obj = e
                    break

    beam_name = getattr(elem_obj, "name", None) if elem_obj else None
    if not beam_name:
        id_str = str(elem_id).strip()
        beam_name = id_str if id_str.upper().startswith("B") else f"B{id_str}"

    return BeamData(
        name=beam_name,
        section=GeometrySection(width_in=w, depth_in=d, cover_in=cover),
        top_bars=tuple(top_rebars),
        bottom_bars=tuple(bottom_rebars),
        stirrups=stirrup_obj,
        schedule=tuple(sched_rows),
        scale=scale,
        unit=unit,
    )


def _element_to_beam_profile_data(
    elem_id: Union[int, str],
    elem_detailing: Any,
    elem_design: Optional[Any],
    model: Optional[Any],
    *,
    project: Optional[Any] = None,
    scale: Any = None,
    unit: Any = None,
) -> BeamProfileData:
    """Convert struct_core detailing/design -> struct_draw BeamProfileData."""
    w, d, cover, length, is_metric = _extract_section_properties(
        elem_id, elem_detailing, elem_design, model, project=project, default_w=12.0, default_d=24.0, default_cover=1.5
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
        scale=scale,
        unit=unit,
    )


def _element_to_footing_data(
    elem_id: Union[int, str],
    elem_detailing: Any,
    elem_design: Optional[Any],
    model: Optional[Any],
    *,
    project: Optional[Any] = None,
    scale: Any = None,
    unit: Any = None,
) -> FootingData:
    """Convert struct_core detailing/design -> struct_draw FootingData with consistent unit scaling."""
    # 1. Determine unit system first
    is_metric = False
    if unit is not None:
        from struct_draw.core.units import DrawingUnit
        if isinstance(unit, DrawingUnit):
            is_metric = unit.is_metric
        elif isinstance(unit, str):
            is_metric = DrawingUnit.from_str(unit).is_metric
        else:
            is_metric = getattr(unit, "is_metric", False)
    elif project is not None or model is not None:
        d_u, _, _ = drawing_unit_from_core(project if project is not None else model)
        is_metric = d_u.is_metric

    # 2. Extract column dimensions - search connected column in model first
    col_w = None
    col_d = None
    col_h = None
    target_node_id = None
    eid_str = str(elem_id).strip()
    if eid_str.upper().startswith("F"):
        try:
            target_node_id = int(eid_str[1:])
        except ValueError:
            target_node_id = eid_str[1:]
    else:
        try:
            target_node_id = int(eid_str)
        except ValueError:
            target_node_id = eid_str

    if model is not None and target_node_id is not None:
        elems = getattr(model, "elements", None) or getattr(model, "members", None) or []
        elem_list = list(elems.values()) if isinstance(elems, dict) else list(elems)
        for cand in elem_list:
            s_n = getattr(cand, "start_node", getattr(cand, "node_i", None))
            e_n = getattr(cand, "end_node", getattr(cand, "node_j", None))
            if s_n == target_node_id or e_n == target_node_id:
                sec_id = getattr(cand, "section_id", None)
                secs = getattr(model, "sections", getattr(model, "cross_sections", None)) or {}
                s_dict = secs if isinstance(secs, dict) else {getattr(s, "id", None): s for s in secs}
                sec_obj = s_dict.get(sec_id) if sec_id else getattr(cand, "section", None)
                if sec_obj is not None:
                    bw = _safe_get(sec_obj, ("b", "width", "width_in", "bw"))
                    bh = _safe_get(sec_obj, ("h", "depth", "depth_in", "height"))
                    if bw is not None and bh is not None:
                        col_w = float(bw)
                        col_d = float(bh)
                        col_len = getattr(cand, "length", None)
                        if col_len is not None:
                            col_h = float(col_len)
                        break

    if col_w is None:
        col_w = _safe_get(elem_detailing, ("col_width_in", "col_width", "column_width", "c1", "col_c1")) or _safe_get(elem_design, ("col_width_in", "col_width", "column_width", "c1", "col_c1"))
    if col_d is None:
        col_d = _safe_get(elem_detailing, ("col_depth_in", "col_depth", "column_depth", "c2", "col_c2")) or _safe_get(elem_design, ("col_depth_in", "col_depth", "column_depth", "c2", "col_c2"))

    # Convert column dimensions to target unit system
    if is_metric:
        if col_w is None:
            col_w = 400.0
        else:
            col_w = float(col_w)
            if col_w <= 2.5:  # meters -> mm (e.g. 0.40 m -> 400.0 mm)
                col_w = col_w * 1000.0
            elif col_w < 50.0:  # inches -> mm (e.g. 16.0 in -> 406.4 mm)
                col_w = col_w * 25.4
        if col_d is None:
            col_d = 400.0
        else:
            col_d = float(col_d)
            if col_d <= 2.5:
                col_d = col_d * 1000.0
            elif col_d < 50.0:
                col_d = col_d * 25.4
        if col_h is not None:
            col_h = float(col_h)
            if col_h <= 10.0:  # meters -> mm
                col_h = col_h * 1000.0
            elif col_h < 150.0:  # inches -> mm
                col_h = col_h * 25.4
        else:
            col_h = 2100.0
    else:
        if col_w is None:
            col_w = 16.0
        else:
            col_w = float(col_w)
            if col_w <= 2.5:
                col_w = col_w * 39.37007874
            elif col_w >= 50.0:
                col_w = col_w / 25.4
        if col_d is None:
            col_d = 16.0
        else:
            col_d = float(col_d)
            if col_d <= 2.5:
                col_d = col_d * 39.37007874
            elif col_d >= 50.0:
                col_d = col_d / 25.4
        if col_h is not None:
            col_h = float(col_h)
            if col_h <= 10.0:
                col_h = col_h * 39.37007874
            elif col_h >= 150.0:
                col_h = col_h / 25.4
        else:
            col_h = 84.0

    # 3. Extract footing plan & thickness dimensions
    raw_l = _safe_get(elem_detailing, ("length_in", "length", "footing_length", "L")) or _safe_get(elem_design, ("length_in", "length", "L"))
    raw_w = _safe_get(elem_detailing, ("width_in", "width", "footing_width", "B")) or _safe_get(elem_design, ("width_in", "width", "B"))
    raw_t = _safe_get(elem_detailing, ("thickness_in", "thickness", "mid_thickness_in", "D")) or _safe_get(elem_design, ("thickness_in", "thickness", "D"))

    if is_metric:
        if raw_l is None:
            flen = 2000.0
        else:
            raw_l = float(raw_l)
            if raw_l <= 4.0:  # meters -> mm (e.g. 2.0 m -> 2000 mm)
                flen = raw_l * 1000.0
            elif raw_l <= 12.0:  # feet -> mm (e.g. 5.0 ft -> 1524 mm)
                flen = raw_l * 304.8
            elif raw_l < 250.0:  # inches -> mm (e.g. 60.0 in -> 1524 mm)
                flen = raw_l * 25.4
            else:
                flen = raw_l

        if raw_w is None:
            fwid = flen
        else:
            raw_w = float(raw_w)
            if raw_w <= 4.0:
                fwid = raw_w * 1000.0
            elif raw_w <= 12.0:
                fwid = raw_w * 304.8
            elif raw_w < 250.0:
                fwid = raw_w * 25.4
            else:
                fwid = raw_w

        if raw_t is None:
            fthk = 450.0
        else:
            raw_t = float(raw_t)
            if raw_t <= 2.5:  # meters -> mm
                fthk = raw_t * 1000.0
            elif raw_t < 50.0:  # inches -> mm (e.g. 16.0 in -> 406.4 mm)
                fthk = raw_t * 25.4
            else:
                fthk = raw_t

        raw_edge = _safe_get(elem_detailing, ("edge_thickness_in", "edge_thickness")) or _safe_get(elem_design, ("edge_thickness_in", "edge_thickness"))
        if raw_edge is not None:
            raw_edge = float(raw_edge)
            edge_thk = raw_edge * 25.4 if raw_edge < 50.0 else raw_edge
        else:
            edge_thk = min(200.0, fthk * 0.5)

        raw_cover = _safe_get(elem_detailing, ("cover_in", "cover"))
        cover = float(raw_cover) * 25.4 if (raw_cover and float(raw_cover) < 10.0) else (float(raw_cover) if raw_cover else 75.0)

        raw_dia = _safe_get(elem_detailing, ("bar_dia_in", "bar_diameter", "bar_dia"))
        bar_dia = float(raw_dia) * 25.4 if (raw_dia and float(raw_dia) < 3.0) else (float(raw_dia) if raw_dia else 12.0)

        raw_sp = _safe_get(elem_detailing, ("bar_spacing_in", "bar_spacing"))
        bar_sp = float(raw_sp) * 25.4 if (raw_sp and float(raw_sp) < 20.0) else (float(raw_sp) if raw_sp else 150.0)

    else:  # imperial
        flen = float(raw_l) if raw_l else 84.0
        if flen >= 250.0:
            flen = flen / 25.4
        fwid = float(raw_w) if raw_w else 84.0
        if fwid >= 250.0:
            fwid = fwid / 25.4
        fthk = float(raw_t) if raw_t else 18.0
        if fthk >= 100.0:
            fthk = fthk / 25.4

        raw_edge = _safe_get(elem_detailing, ("edge_thickness_in", "edge_thickness")) or _safe_get(elem_design, ("edge_thickness_in", "edge_thickness"))
        edge_thk = float(raw_edge) if raw_edge else 10.0
        if edge_thk >= 100.0:
            edge_thk = edge_thk / 25.4

        raw_cover = _safe_get(elem_detailing, ("cover_in", "cover"))
        cover = float(raw_cover) / 25.4 if (raw_cover and float(raw_cover) >= 20.0) else (float(raw_cover) if raw_cover else 3.0)

        raw_dia = _safe_get(elem_detailing, ("bar_dia_in", "bar_diameter", "bar_dia"))
        bar_dia = float(raw_dia) / 25.4 if (raw_dia and float(raw_dia) >= 6.0) else (float(raw_dia) if raw_dia else 0.625)

        raw_sp = _safe_get(elem_detailing, ("bar_spacing_in", "bar_spacing"))
        bar_sp = float(raw_sp) / 25.4 if (raw_sp and float(raw_sp) >= 50.0) else (float(raw_sp) if raw_sp else 6.0)

    # 4. Schedule rows
    sched_rows: List[ScheduleRow] = []
    schedule = getattr(elem_detailing, "bar_schedule", None)
    if schedule and hasattr(schedule, "items"):
        for item in schedule.items:
            b_size = getattr(item, "bar_size", getattr(item, "size", 4 if not is_metric else 12))
            b_size_str = f"#{b_size}" if not is_metric and not str(b_size).startswith("#") else (f"T{b_size}" if is_metric and not str(b_size).startswith("T") else str(b_size))
            b_qty = getattr(item, "quantity", getattr(item, "count", 1))
            raw_cut_len = float(getattr(item, "cut_length", flen))
            if is_metric and raw_cut_len < 250.0:
                cut_len_disp = raw_cut_len * 25.4
            elif (not is_metric) and raw_cut_len >= 250.0:
                cut_len_disp = raw_cut_len / 25.4
            else:
                cut_len_disp = raw_cut_len
            sched_rows.append(
                ScheduleRow(
                    mark=getattr(item, "mark", ""),
                    size=b_size_str,
                    quantity=int(b_qty),
                    length_in=cut_len_disp,
                    remarks=getattr(item, "shape_code", "") or getattr(item, "location", ""),
                    shape_code=getattr(item, "shape_code", ""),
                    total_weight=float(getattr(item, "weight", 0.0) or 0.0),
                )
            )

    if is_metric:
        return FootingData.from_metric(
            name=f"F{elem_id}",
            length=flen,
            width=fwid,
            mid_thick=fthk,
            edge_thick=edge_thk,
            col_width=float(col_w),
            col_depth=float(col_d),
            col_height=col_h,
            fd_depth=1500.0,
            pl_height=300.0,
            cover=cover,
            bar_dia=bar_dia,
            bar_spacing=bar_sp,
            ld=600.0,
            ledge=100.0,
            pcc_thick=75.0,
            soling_thick=75.0,
            schedule=tuple(sched_rows),
            scale=scale,
            unit=unit,
        )
    else:
        return FootingData(
            name=f"F{elem_id}",
            length_in=flen,
            width_in=fwid,
            mid_thickness_in=fthk,
            edge_thickness_in=edge_thk,
            column_width_in=float(col_w),
            column_depth_in=float(col_d),
            column_height_in=col_h,
            footing_depth_in=60.0,
            plinth_height_in=12.0,
            cover_in=cover,
            bar_dia_in=bar_dia,
            bar_spacing_in=bar_sp,
            development_length_in=24.0,
            ledge_in=4.0,
            pcc_thickness_in=3.0,
            soling_thickness_in=3.0,
            schedule=tuple(sched_rows),
            scale=scale,
            unit=unit,
        )


def _element_to_combined_footing_data(
    elem_id: Union[int, str],
    elem_detailing: Any,
    elem_design: Optional[Any],
    model: Optional[Any],
    *,
    project: Optional[Any] = None,
    scale: Any = None,
    unit: Any = None,
) -> CombinedFootingData:
    """Convert struct_core detailing/design -> struct_draw CombinedFootingData."""
    proj_l = float(_safe_get(elem_detailing, ("proj_left_in", "cantilever_left")) or _safe_get(elem_design, ("proj_left_in", "cantilever_left")) or 30.0)
    proj_r = float(_safe_get(elem_detailing, ("proj_right_in", "cantilever_right")) or _safe_get(elem_design, ("proj_right_in", "cantilever_right")) or 30.0)
    col_sp = float(_safe_get(elem_detailing, ("col_spacing_in", "column_spacing")) or _safe_get(elem_design, ("col_spacing_in", "column_spacing")) or 120.0)
    w = float(_safe_get(elem_detailing, ("width_in", "width")) or _safe_get(elem_design, ("width_in", "width")) or 60.0)
    thk = float(_safe_get(elem_detailing, ("thickness_in", "thickness")) or _safe_get(elem_design, ("thickness_in", "thickness")) or 24.0)

    is_metric = False
    if unit is not None:
        is_metric = getattr(unit, "is_metric", False)
    elif proj_l >= 500.0 or col_sp >= 1000.0:
        is_metric = True

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
        scale=scale,
        unit=unit,
    )


def _element_to_column_data(
    elem_id: Union[int, str],
    elem_detailing: Any,
    elem_design: Optional[Any],
    model: Optional[Any],
    *,
    project: Optional[Any] = None,
    scale: Any = None,
    unit: Any = None,
) -> ColumnData:
    """Convert struct_core detailing/design/model -> struct_draw ColumnData."""
    w, d, cover, length, is_metric = _extract_section_properties(
        elem_id, elem_detailing, elem_design, model, project=project, default_w=16.0, default_d=16.0, default_cover=1.5, default_length=144.0
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

    elem_obj = None
    if model is not None and hasattr(model, "elements"):
        elems = getattr(model, "elements", [])
        if isinstance(elems, dict):
            elem_obj = elems.get(elem_id)
        elif isinstance(elems, (list, tuple)):
            for e in elems:
                if getattr(e, "id", None) == elem_id:
                    elem_obj = e
                    break

    col_name = getattr(elem_obj, "name", None) if elem_obj else None
    if not col_name:
        id_str = str(elem_id).strip()
        col_name = id_str if id_str.upper().startswith("C") else f"C{id_str}"

    sched_rows: List[ScheduleRow] = []
    schedule = getattr(elem_detailing, "bar_schedule", None)
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
                    remarks=getattr(item, "shape_code", "") or getattr(item, "location", ""),
                    shape_code=getattr(item, "shape_code", ""),
                    total_weight=float(getattr(item, "weight", 0.0) or 0.0),
                )
            )

    return ColumnData(
        name=col_name,
        section=GeometrySection(width_in=w, depth_in=d, cover_in=cover),
        height_in=float(length),
        longitudinal_bars=tuple(bars_list),
        stirrups=tie_obj,
        schedule=tuple(sched_rows),
        scale=scale,
        unit=unit,
    )


def _element_to_staircase_data(
    elem_id: Union[int, str],
    elem_detailing: Any,
    elem_design: Optional[Any],
    model: Optional[Any],
    *,
    project: Optional[Any] = None,
    scale: Any = None,
    unit: Any = None,
) -> StaircaseData:
    """Convert struct_core detailing/design -> struct_draw StaircaseData."""
    f_w = float(_safe_get(elem_detailing, ("flight_width_in", "flight_width", "width")) or _safe_get(elem_design, ("flight_width_in", "flight_width", "width")) or 48.0)
    riser = float(_safe_get(elem_detailing, ("riser_height_in", "riser_height", "riser")) or _safe_get(elem_design, ("riser_height_in", "riser_height", "riser")) or 6.0)
    tread = float(_safe_get(elem_detailing, ("tread_depth_in", "tread_depth", "tread")) or _safe_get(elem_design, ("tread_depth_in", "tread_depth", "tread")) or 10.0)
    n_risers = int(_safe_get(elem_detailing, ("num_risers", "steps")) or _safe_get(elem_design, ("num_risers", "steps")) or 10)
    slab_thk = float(_safe_get(elem_detailing, ("slab_thickness_in", "waist_thickness", "thickness")) or _safe_get(elem_design, ("slab_thickness_in", "waist_thickness", "thickness")) or 6.0)

    is_metric = False
    if unit is not None:
        is_metric = getattr(unit, "is_metric", False)
    elif f_w >= 500.0 or riser >= 50.0:
        is_metric = True

    return StaircaseData(
        name=f"ST{elem_id}",
        flight_width_in=f_w if not is_metric else (f_w if f_w >= 500 else 1200.0),
        riser_height_in=riser if not is_metric else (riser if riser >= 50 else 150.0),
        tread_depth_in=tread if not is_metric else (tread if tread >= 100 else 250.0),
        num_risers=n_risers,
        slab_thickness_in=slab_thk if not is_metric else (slab_thk if slab_thk >= 50 else 150.0),
        scale=scale,
        unit=unit,
    )


def _element_to_slab_data(
    elem_id: Union[int, str],
    elem_detailing: Any,
    elem_design: Optional[Any],
    model: Optional[Any],
    *,
    project: Optional[Any] = None,
    scale: Any = None,
    unit: Any = None,
) -> SlabData:
    """Convert struct_core detailing/design -> struct_draw SlabData."""
    length = float(_safe_get(elem_detailing, ("length_in", "length", "lx")) or _safe_get(elem_design, ("length_in", "length", "lx")) or 240.0)
    width = float(_safe_get(elem_detailing, ("width_in", "width", "ly")) or _safe_get(elem_design, ("width_in", "width", "ly")) or 180.0)
    thk = float(_safe_get(elem_detailing, ("thickness_in", "thickness", "h")) or _safe_get(elem_design, ("thickness_in", "thickness", "h")) or 6.0)
    cover = float(_safe_get(elem_detailing, ("cover_in", "cover")) or _safe_get(elem_design, ("cover_in", "cover")) or 0.75)

    is_metric = False
    if unit is not None:
        is_metric = getattr(unit, "is_metric", False)
    elif length >= 1000.0 or width >= 1000.0 or thk >= 50.0:
        is_metric = True

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
        scale=scale,
        unit=unit,
    )


# ---------------------------------------------------------------------------
# General Framing / Arrangement extractor
# ---------------------------------------------------------------------------


def _cluster_coords(coords: Sequence[float], tol: float = 50.0) -> List[float]:
    """Cluster 1D coordinates within tolerance and return sorted unique coordinates."""
    if not coords:
        return [0.0]
    sorted_c = sorted(coords)
    clusters: List[float] = [sorted_c[0]]
    for c in sorted_c[1:]:
        if abs(c - clusters[-1]) > tol:
            clusters.append(c)
    return clusters


def _detect_model_units_and_scale(
    model: Any,
    project: Optional[Any],
    nodes: Sequence[Any],
    sections: Sequence[Any],
) -> Tuple[bool, float, float]:
    """
    Determine whether model is metric (SI) or imperial, and calculate coordinate
    and section scale factors so struct_draw receives millimeter or inch values.
    """
    # 1. Check explicit project metadata units or model units
    target = project if project is not None else model
    if target is not None:
        meta = getattr(target, "metadata", None)
        if (meta and getattr(meta, "units", None) is not None) or getattr(target, "units", None) is not None:
            u, c_scale, s_scale = drawing_unit_from_core(target)
            return u.is_metric, c_scale, s_scale

    if project is not None and getattr(project, "metadata", None) is not None:
        meta_units = getattr(project.metadata, "units", None)
        if meta_units is not None:
            u_sys = str(getattr(meta_units, "system", "")).lower()
            u_len = str(getattr(meta_units, "length", "")).lower()
            if u_sys in ("imperial", "us_customary") or u_len in ("in", "inch", "ft", "foot", "feet"):
                c_scale = 12.0 if u_len in ("ft", "foot", "feet") else 1.0
                return False, c_scale, 1.0
            elif u_sys in ("metric", "si") or u_len in ("m", "meter", "meters", "mm"):
                c_scale = 1.0 if u_len == "mm" else 1000.0
                s_scale = 1.0 if u_len == "mm" else 1000.0
                return True, c_scale, s_scale

    # 2. Heuristic detection from coordinates and section dimensions
    max_coord = max((abs(float(getattr(n, a, 0.0))) for n in nodes for a in ("x", "y", "z")), default=0.0)

    sec_dims: List[float] = []
    for s in sections:
        for attr in ("b", "h", "d", "width", "depth"):
            v = getattr(s, attr, None)
            if v is not None and float(v) > 0:
                sec_dims.append(float(v))
    max_sec = max(sec_dims, default=0.4)

    # Standard metric model in meters: section <= 2.5m (or <= 5m with building coord <= 200m)
    if max_sec <= 2.5 or (max_sec <= 5.0 and max_coord <= 200.0):
        return True, 1000.0, 1000.0
    # Model already in millimeters
    if max_sec >= 100.0 or max_coord >= 1000.0:
        return True, 1.0, 1.0
    # Model in US Customary
    if 2.5 < max_sec < 100.0:
        c_scale = 12.0 if max_coord <= 250.0 else 1.0
        return False, c_scale, 1.0

    return True, 1000.0, 1000.0


def create_general_frame_data_from_model(
    model_or_project: Union[StructuralModel, Project, Any],
    *,
    view_mode: str = "both",  # "both", "plan", "elevation"
    story_level: Optional[Union[str, int, float]] = None,
    grid_line: Optional[Union[str, float]] = None,
    view_axis: Optional[str] = None,  # "X" or "Y" (for 3D frame elevation)
    title: Optional[str] = None,
    scale: Optional[Union[str, DrawingScale]] = None,
    unit: Optional[Union[str, DrawingUnit]] = None,
) -> GeneralFrameData:
    """
    Convert a structural model (nodes, elements, sections, story elevations) into
    a comprehensive GeneralFrameData representation tailored for framing plans or elevations.

    Features:
    * Automatic unit detection & scaling (meters to mm for standard SI models).
    * Automatic 2D vs 3D frame geometry detection.
    * Automated grid clustering (A, B, C... and 1, 2, 3...).
    * Automated story elevation levels (GL, FL1, FL2... ROOF).
    * Automated member classification (columns, beams, braces/trusses).
    * Cross-section lookup from RectangularSection, CircularSection, or GeneralSection.
    * Level filtering for Framing Plans (e.g. story_level='FL1' or 'ROOF').
    * Grid-plane filtering for Frame Elevations (e.g. grid_line='1' or 'A').
    """
    project = model_or_project if isinstance(model_or_project, Project) else None
    model = getattr(model_or_project, "model", model_or_project)

    # 1. Extract raw nodes
    raw_nodes = getattr(model, "nodes", None) or []
    if isinstance(raw_nodes, dict):
        raw_nodes_list = list(raw_nodes.values())
    else:
        raw_nodes_list = list(raw_nodes)

    # Extract raw sections
    raw_sections = getattr(model, "sections", None) or []
    if isinstance(raw_sections, dict):
        raw_sections_list = list(raw_sections.values())
    else:
        raw_sections_list = list(raw_sections)

    # 2. Units & Scaling
    is_metric, coord_scale, sec_scale = _detect_model_units_and_scale(model, project, raw_nodes_list, raw_sections_list)
    if unit is not None:
        d_unit = DrawingUnit.from_str(str(unit))
        is_metric = d_unit.is_metric
    else:
        d_unit = DrawingUnit.MM if is_metric else DrawingUnit.IN

    if not raw_nodes_list:
        return GeneralFrameData.from_grid(
            name=getattr(model, "name", "MODEL-FRAME"),
            bays=(6000.0, 6000.0, 6000.0) if is_metric else (240.0, 240.0, 240.0),
            story_heights=(4000.0, 3500.0, 3500.0) if is_metric else (144.0, 120.0, 120.0),
            col_width=400.0 if is_metric else 16.0,
            col_depth=400.0 if is_metric else 16.0,
            beam_width=300.0 if is_metric else 12.0,
            beam_depth=500.0 if is_metric else 20.0,
            title=title or "BUILDING GENERAL FRAMING ELEVATION",
            is_metric=is_metric,
            scale=scale,
            unit=d_unit,
        )

    # 3. Scaled coordinates
    scaled_nodes: Dict[Any, Tuple[float, float, float]] = {}
    for idx, n in enumerate(raw_nodes_list):
        nid = getattr(n, "id", idx + 1)
        nx = float(getattr(n, "x", 0.0)) * coord_scale
        ny = float(getattr(n, "y", 0.0)) * coord_scale
        nz = float(getattr(n, "z", 0.0)) * coord_scale
        scaled_nodes[nid] = (nx, ny, nz)

    x_vals = [c[0] for c in scaled_nodes.values()]
    y_vals = [c[1] for c in scaled_nodes.values()]
    z_vals = [c[2] for c in scaled_nodes.values()]
    is_3d = (max(z_vals) - min(z_vals)) > 20.0

    # 4. Story Elevations
    raw_elevs = getattr(model, "story_elevations", None)
    if raw_elevs and len(raw_elevs) > 0:
        elev_vals = _cluster_coords([float(e) * coord_scale for e in raw_elevs], tol=50.0)
    else:
        vert_vals = z_vals if is_3d else y_vals
        elev_vals = _cluster_coords(vert_vals, tol=50.0)

    level_lines: List[FrameLevelLine] = []
    num_levels = len(elev_vals)
    for idx, ev in enumerate(elev_vals):
        if idx == 0:
            lbl = "BASE" if ev < 0 else "GL"
        elif idx == num_levels - 1 and num_levels > 1:
            lbl = "ROOF"
        else:
            lbl = f"FL{idx}"
        level_lines.append(FrameLevelLine(label=lbl, elevation=ev))

    # 5. Grid Lines
    explicit_grids = getattr(model, "grids", None) or getattr(model, "grid_lines", None)
    grid_x_list: List[FrameGridLine] = []
    grid_y_list: List[FrameGridLine] = []

    if isinstance(explicit_grids, dict):
        for g_lbl, g_val in explicit_grids.items():
            g_coord = float(g_val) * coord_scale
            if str(g_lbl).isalpha():
                grid_x_list.append(FrameGridLine(label=str(g_lbl), coord=g_coord, axis="X"))
            else:
                grid_y_list.append(FrameGridLine(label=str(g_lbl), coord=g_coord, axis="Y"))
    elif isinstance(explicit_grids, (list, tuple)) and len(explicit_grids) > 0:
        for g_obj in explicit_grids:
            lbl = str(getattr(g_obj, "label", getattr(g_obj, "name", "A")))
            g_coord = float(getattr(g_obj, "coord", getattr(g_obj, "coordinate", 0.0))) * coord_scale
            ax = str(getattr(g_obj, "axis", "X" if lbl.isalpha() else "Y")).upper()
            if ax == "X":
                grid_x_list.append(FrameGridLine(label=lbl, coord=g_coord, axis="X"))
            else:
                grid_y_list.append(FrameGridLine(label=lbl, coord=g_coord, axis="Y"))

    if not grid_x_list:
        x_clusters = _cluster_coords(x_vals, tol=50.0)
        for i, xc in enumerate(x_clusters):
            lbl = chr(65 + i) if i < 26 else f"X{i+1}"
            grid_x_list.append(FrameGridLine(label=lbl, coord=xc, axis="X"))

    if not grid_y_list:
        y_clusters = _cluster_coords(y_vals, tol=50.0)
        for j, yc in enumerate(y_clusters):
            lbl = str(j + 1)
            grid_y_list.append(FrameGridLine(label=lbl, coord=yc, axis="Y"))

    # 6. Sections Map
    sections_map: Dict[Any, Tuple[float, float, str]] = {}
    for s in raw_sections_list:
        sid = getattr(s, "id", None)
        if sid is None:
            continue
        s_name = getattr(s, "name", None)
        if hasattr(s, "b") and hasattr(s, "h"):
            w = float(s.b) * sec_scale
            d = float(s.h) * sec_scale
            name = s_name or f"{int(w)}x{int(d)}"
            sections_map[sid] = (w, d, name)
        elif hasattr(s, "d"):
            dia = float(s.d) * sec_scale
            name = s_name or f"D{int(dia)}"
            sections_map[sid] = (dia, dia, name)
        else:
            A = float(getattr(s, "A", 0.16))
            dim = math.sqrt(A) * sec_scale if A > 0 else (400.0 if is_metric else 16.0)
            name = s_name or f"{int(dim)}x{int(dim)}"
            sections_map[sid] = (dim, dim, name)

    # 7. Elements Extraction & Classification
    raw_elements = getattr(model, "elements", None) or getattr(model, "members", None) or []
    if isinstance(raw_elements, dict):
        raw_elements_list = list(raw_elements.values())
    else:
        raw_elements_list = list(raw_elements)

    all_members: List[FrameMember] = []
    col_count = 0
    beam_count = 0
    brace_count = 0

    for idx, elem in enumerate(raw_elements_list):
        eid = getattr(elem, "id", f"E{idx+1}")
        sn = getattr(elem, "start_node", getattr(elem, "node_i", 1))
        en = getattr(elem, "end_node", getattr(elem, "node_j", 2))
        p1 = scaled_nodes.get(sn)
        p2 = scaled_nodes.get(en)
        if not p1 or not p2:
            continue

        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dz = p2[2] - p1[2]
        length = math.hypot(math.hypot(dx, dy), dz)
        if length < 1e-3:
            continue

        given_type = str(getattr(elem, "member_type", getattr(elem, "type", ""))).lower()
        if is_3d:
            vert_ratio = abs(dz) / length
            if vert_ratio > 0.85:
                m_type = "column"
            elif vert_ratio < 0.15:
                m_type = "beam"
            elif given_type == "truss":
                m_type = "truss"
            else:
                m_type = "brace"
        else:
            vert_ratio = abs(dy) / length
            if vert_ratio > 0.85:
                m_type = "column"
            elif vert_ratio < 0.15:
                m_type = "beam"
            elif given_type == "truss":
                m_type = "truss"
            else:
                m_type = "brace"

        sec_id = getattr(elem, "section_id", None)
        if sec_id in sections_map:
            w, d, sec_name = sections_map[sec_id]
        else:
            def_w = 400.0 if m_type == "column" else (300.0 if is_metric else 12.0)
            def_d = 400.0 if m_type == "column" else (500.0 if is_metric else 20.0)
            w = float(_safe_get(elem, ("width_in", "width", "b", "bw")) or def_w)
            d = float(_safe_get(elem, ("depth_in", "depth", "h", "height")) or def_d)
            sec_name = f"{int(w)}x{int(d)}"

        elem_name = getattr(elem, "name", None)
        if not elem_name:
            raw_id = getattr(elem, "id", None)
            if raw_id is not None and str(raw_id).strip():
                id_str = str(raw_id).strip()
                prefix = {"column": "C", "beam": "B", "truss": "T", "brace": "BR"}.get(m_type, "M")
                if id_str.upper().startswith(prefix):
                    elem_name = id_str
                else:
                    elem_name = f"{prefix}{id_str}"
            else:
                if m_type == "column":
                    col_count += 1
                    elem_name = f"C{col_count}"
                elif m_type == "beam":
                    beam_count += 1
                    elem_name = f"B{beam_count}"
                elif m_type == "truss":
                    elem_name = f"T{idx+1}"
                else:
                    brace_count += 1
                    elem_name = f"BR{brace_count}"

        all_members.append(
            FrameMember(
                id=eid,
                start_node=sn,
                end_node=en,
                member_type=m_type,
                name=elem_name,
                section_name=sec_name,
                width_in=w,
                depth_in=d,
            )
        )

    model_title = title or getattr(model, "name", "STRUCTURAL MODEL")

    # 8. View-Specific Construction
    if view_mode == "plan":
        # Resolve target floor elevation
        target_elev = None
        target_lbl = None
        if story_level is not None:
            s_str = str(story_level).strip()
            for lvl in level_lines:
                if lvl.label.upper() == s_str.upper() or s_str.upper() in lvl.label.upper():
                    target_elev = lvl.elevation
                    target_lbl = lvl.label
                    break
            if target_elev is None:
                try:
                    val = float(story_level)
                    if val.is_integer() and 0 <= int(val) < len(elev_vals):
                        target_elev = elev_vals[int(val)]
                        target_lbl = level_lines[int(val)].label
                    else:
                        target_elev = min(elev_vals, key=lambda e: abs(e - val))
                        for lvl in level_lines:
                            if abs(lvl.elevation - target_elev) < 50.0:
                                target_lbl = lvl.label
                                break
                except ValueError:
                    pass

        if target_elev is None:
            if len(elev_vals) > 1:
                target_elev = elev_vals[-1]
                target_lbl = level_lines[-1].label
            else:
                target_elev = elev_vals[0]
                target_lbl = level_lines[0].label

        plan_members: List[FrameMember] = []
        plan_nodes: Dict[Any, FrameNode] = {}

        for m in all_members:
            p1 = scaled_nodes.get(m.start_node)
            p2 = scaled_nodes.get(m.end_node)
            if not p1 or not p2:
                continue

            z1 = p1[2] if is_3d else p1[1]
            z2 = p2[2] if is_3d else p2[1]

            if m.member_type == "beam":
                # Include beam if its floor matches target elevation
                if abs(z1 - target_elev) < 300.0 or abs(z2 - target_elev) < 300.0:
                    plan_members.append(m)
                    if m.start_node not in plan_nodes:
                        plan_nodes[m.start_node] = FrameNode(id=m.start_node, x=p1[0], y=p1[1] if is_3d else 0.0, z=0.0)
                    if m.end_node not in plan_nodes:
                        plan_nodes[m.end_node] = FrameNode(id=m.end_node, x=p2[0], y=p2[1] if is_3d else 0.0, z=0.0)

            elif m.member_type == "column":
                # Include column if it connects to target elevation
                if min(z1, z2) - 100.0 <= target_elev <= max(z1, z2) + 100.0:
                    plan_members.append(m)
                    # Node coordinates at target elevation
                    col_node = m.end_node if abs(z2 - target_elev) < abs(z1 - target_elev) else m.start_node
                    cp = scaled_nodes[col_node]
                    plan_nodes[col_node] = FrameNode(id=col_node, x=cp[0], y=cp[1] if is_3d else 0.0, z=0.0)

        # Fallback if no beams matched target elevation: include all members mapped to plan
        if not plan_members:
            plan_members = all_members
            for nid, p in scaled_nodes.items():
                plan_nodes[nid] = FrameNode(id=nid, x=p[0], y=p[1] if is_3d else 0.0, z=0.0)

        plan_title = title or f"{model_title} - {target_lbl} FRAMING PLAN (EL. {target_elev:.0f})"
        return GeneralFrameData(
            name=getattr(model, "name", "MODEL-PLAN"),
            nodes=tuple(plan_nodes.values()),
            members=tuple(plan_members),
            grid_x=tuple(grid_x_list),
            grid_y=tuple(grid_y_list),
            levels=tuple(level_lines),
            title=plan_title,
            view_mode="plan",
            is_metric=is_metric,
            scale=scale,
            unit=d_unit,
        )

    elif view_mode == "elevation":
        if not is_3d:
            # 2D frame: all members are in elevation plane
            elev_nodes_2d = [FrameNode(id=nid, x=p[0], y=p[1], z=0.0) for nid, p in scaled_nodes.items()]
            elev_title = title or f"{model_title} - FRAME ELEVATION"
            return GeneralFrameData(
                name=getattr(model, "name", "MODEL-FRAME"),
                nodes=tuple(elev_nodes_2d),
                members=tuple(all_members),
                grid_x=tuple(grid_x_list),
                grid_y=tuple(grid_y_list),
                levels=tuple(level_lines),
                title=elev_title,
                view_mode="elevation",
                is_metric=is_metric,
                scale=scale,
                unit=d_unit,
            )

        # 3D frame elevation: resolve grid line plane
        matched_grid = None
        is_y_plane = True
        if grid_line is not None:
            g_str = str(grid_line).strip().upper()
            for gy in grid_y_list:
                if gy.label.upper() == g_str:
                    matched_grid = gy
                    is_y_plane = True
                    break
            if matched_grid is None:
                for gx in grid_x_list:
                    if gx.label.upper() == g_str:
                        matched_grid = gx
                        is_y_plane = False
                        break

        if matched_grid is None:
            if view_axis and str(view_axis).upper() == "X":
                matched_grid = grid_x_list[0] if grid_x_list else FrameGridLine(label="A", coord=0.0, axis="X")
                is_y_plane = False
            else:
                matched_grid = grid_y_list[0] if grid_y_list else (grid_x_list[0] if grid_x_list else FrameGridLine(label="1", coord=0.0, axis="Y"))
                is_y_plane = (matched_grid.axis == "Y")

        target_coord = matched_grid.coord
        elev_members: List[FrameMember] = []
        elev_nodes_dict: Dict[Any, FrameNode] = {}

        for m in all_members:
            p1 = scaled_nodes.get(m.start_node)
            p2 = scaled_nodes.get(m.end_node)
            if not p1 or not p2:
                continue

            if is_y_plane:
                if abs(p1[1] - target_coord) < 250.0 and abs(p2[1] - target_coord) < 250.0:
                    elev_members.append(m)
                    if m.start_node not in elev_nodes_dict:
                        elev_nodes_dict[m.start_node] = FrameNode(id=m.start_node, x=p1[0], y=p1[2], z=0.0)
                    if m.end_node not in elev_nodes_dict:
                        elev_nodes_dict[m.end_node] = FrameNode(id=m.end_node, x=p2[0], y=p2[2], z=0.0)
            else:
                if abs(p1[0] - target_coord) < 250.0 and abs(p2[0] - target_coord) < 250.0:
                    elev_members.append(m)
                    if m.start_node not in elev_nodes_dict:
                        elev_nodes_dict[m.start_node] = FrameNode(id=m.start_node, x=p1[1], y=p1[2], z=0.0)
                    if m.end_node not in elev_nodes_dict:
                        elev_nodes_dict[m.end_node] = FrameNode(id=m.end_node, x=p2[1], y=p2[2], z=0.0)

        if not elev_members:
            elev_members = all_members
            for nid, p in scaled_nodes.items():
                span_coord = p[0] if is_y_plane else p[1]
                elev_nodes_dict[nid] = FrameNode(id=nid, x=span_coord, y=p[2], z=0.0)

        elev_grids = grid_x_list if is_y_plane else grid_y_list
        elev_title = title or f"{model_title} - ELEVATION GRID {matched_grid.label}"
        return GeneralFrameData(
            name=getattr(model, "name", "MODEL-FRAME"),
            nodes=tuple(elev_nodes_dict.values()),
            members=tuple(elev_members),
            grid_x=tuple(elev_grids),
            grid_y=tuple(grid_y_list),
            levels=tuple(level_lines),
            title=elev_title,
            view_mode="elevation",
            is_metric=is_metric,
            scale=scale,
            unit=d_unit,
        )

    else:
        # view_mode == "both"
        frame_nodes = [FrameNode(id=nid, x=p[0], y=p[1], z=p[2]) for nid, p in scaled_nodes.items()]
        combined_title = title or f"{model_title} - GENERAL FRAMING"
        return GeneralFrameData(
            name=getattr(model, "name", "MODEL-FRAME"),
            nodes=tuple(frame_nodes),
            members=tuple(all_members),
            grid_x=tuple(grid_x_list),
            grid_y=tuple(grid_y_list),
            levels=tuple(level_lines),
            title=combined_title,
            view_mode="both",
            is_metric=is_metric,
            scale=scale,
            unit=d_unit,
        )


def _model_to_general_frame_data(
    model: Any,
    *,
    view_mode: str = "both",
    title: Optional[str] = None,
) -> GeneralFrameData:
    """Backward-compatible alias for create_general_frame_data_from_model."""
    return create_general_frame_data_from_model(model, view_mode=view_mode, title=title)


__all__ = [
    "draw_from_core",
    "draw_general_frame_from_core",
    "draw_framing_plan_from_core",
    "draw_frame_elevation_from_core",
    "create_general_frame_data_from_model",
]


