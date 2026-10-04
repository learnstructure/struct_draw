"""struct_draw.elements.general_frame — General Arrangement (GA) framing drawings.

Renders 2D/3D structural framing plans, frame elevations, and truss outlines:
* Framing Plan: Columns, beams, secondary joists, grid bubbles, bay dimensions, and member marks.
* Frame Elevation: Columns, beams, braces, story levels, grid lines, story height dimensions.
* Truss Outline: Top chords, bottom chords, vertical struts, diagonals, gussets, pitch dimensions.

All rendered strictly as geometric outlines without reinforcement/rebar detailing.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

from struct_draw.core.composite import (
    draw_circle,
    draw_concrete_outline,
    draw_dimension,
    draw_level_marker,
    draw_line,
    draw_polyline,
    draw_rectangle,
    draw_text,
)
from struct_draw.core.data import (
    FrameElevationData,
    FrameGridLine,
    FrameLevelLine,
    FrameMember,
    FrameNode,
    FramingPlanData,
    GeneralFrameData,
    TrussData,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _detect_metric(data: Any) -> bool:
    """Determine whether data is in metric units (mm) or imperial (inches)."""
    if getattr(data, "is_metric", None) is not None:
        return bool(data.is_metric)
    if isinstance(data, FramingPlanData):
        if any(b > 1000.0 for b in data.grid_x) or any(b > 1000.0 for b in data.grid_y):
            return True
        if data.col_width_in > 100.0 or data.beam_depth_in > 100.0:
            return True
    elif isinstance(data, FrameElevationData):
        if any(b > 1000.0 for b in data.bays) or any(h > 1000.0 for h in data.story_heights):
            return True
        if data.col_width_in > 100.0 or data.beam_depth_in > 100.0:
            return True
    elif isinstance(data, GeneralFrameData):
        if data.grid_x and any(g.coord > 1000.0 for g in data.grid_x):
            return True
        if data.levels and any(l.elevation > 1000.0 for l in data.levels):
            return True
        if data.nodes and any(n.x > 1000.0 or n.y > 1000.0 for n in data.nodes):
            return True
        if data.members and any(m.width_in > 100.0 or m.depth_in > 100.0 for m in data.members):
            return True
    return False


# ---------------------------------------------------------------------------
# Framing Plan View
# ---------------------------------------------------------------------------


def plan_view(
    target: Any,
    data: FramingPlanData | GeneralFrameData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Draw a structural framing plan view (columns, beams, grids, dimensions, callouts)."""
    ox, oy = origin
    scale = kwargs.get("scale", getattr(data, "scale", None))
    unit = kwargs.get("unit", getattr(data, "unit", None))
    is_metric = unit.is_metric if unit is not None else _detect_metric(data)

    if scale is not None or unit is not None:
        from struct_draw.core.units import DrawingScale, DrawingUnit, SCALE_1_100, SCALE_1_8_IN
        from struct_draw.style.annotation_config import DEFAULT_ANNOTATION_CONFIG
        d_unit = unit or (DrawingUnit.MM if is_metric else DrawingUnit.IN)
        d_scale = scale or (SCALE_1_100 if is_metric else SCALE_1_8_IN)
        text_size = DEFAULT_ANNOTATION_CONFIG.text_height(d_scale, d_unit)
        bubble_radius = DEFAULT_ANNOTATION_CONFIG.bubble_radius(d_scale, d_unit)
        dim_offset = DEFAULT_ANNOTATION_CONFIG.dim_offset(d_scale, d_unit)
        dimstyle = "DIM_PLAN" if is_metric else "Linear"
    else:
        text_size = 200.0 if is_metric else 8.0
        bubble_radius = 250.0 if is_metric else 10.0
        dim_offset = 600.0 if is_metric else 24.0
        dimstyle = "Metric" if is_metric else "Linear"

    # Extract or build grid coordinates
    if isinstance(data, FramingPlanData):
        bays_x = list(data.grid_x)
        bays_y = list(data.grid_y)
        col_w = data.col_width_in
        col_d = data.col_depth_in
        beam_w = data.beam_width_in
        beam_d = data.beam_depth_in
        labels_x = list(data.grid_labels_x) if data.grid_labels_x else [chr(65 + i) for i in range(len(bays_x) + 1)]
        labels_y = list(data.grid_labels_y) if data.grid_labels_y else [str(i + 1) for i in range(len(bays_y) + 1)]
        plan_title = title or (data.title if "PLAN" in data.title.upper() else f"{data.title} - {data.level_name} PLAN")
        sec_beams = data.secondary_beams
    else:
        # GeneralFrameData
        if data.grid_x and data.grid_y:
            x_coords = [g.coord for g in data.grid_x]
            y_coords = [g.coord for g in data.grid_y]
            labels_x = [g.label for g in data.grid_x]
            labels_y = [g.label for g in data.grid_y]
            bays_x = [x_coords[i + 1] - x_coords[i] for i in range(len(x_coords) - 1)]
            bays_y = [y_coords[i + 1] - y_coords[i] for i in range(len(y_coords) - 1)]
        else:
            bays_x = [240.0, 240.0, 240.0] if not is_metric else [6000.0, 6000.0, 6000.0]
            bays_y = [240.0, 240.0] if not is_metric else [6000.0, 6000.0]
            labels_x = [chr(65 + i) for i in range(len(bays_x) + 1)]
            labels_y = [str(i + 1) for i in range(len(bays_y) + 1)]
        col_w = 16.0 if not is_metric else 400.0
        col_d = 16.0 if not is_metric else 400.0
        beam_w = 12.0 if not is_metric else 300.0
        beam_d = 20.0 if not is_metric else 500.0
        
        # Derive title ensuring it says PLAN and not Elevation & Plan
        if title:
            plan_title = title
        else:
            raw_title = getattr(data, "title", "STRUCTURAL FRAMING")
            upper = raw_title.upper()
            if "ELEVATION & PLAN" in upper:
                plan_title = raw_title.replace("ELEVATION & PLAN", "FRAMING PLAN").replace("Elevation & Plan", "Framing Plan").replace("Elevation & plan", "Framing Plan")
            elif "ELEVATION AND PLAN" in upper:
                plan_title = raw_title.replace("ELEVATION AND PLAN", "FRAMING PLAN").replace("Elevation and Plan", "Framing Plan")
            elif "PLAN" in upper and "ELEVATION" not in upper:
                plan_title = raw_title
            elif "ELEVATION" in upper and "PLAN" not in upper:
                plan_title = raw_title.replace("ELEVATION", "FRAMING PLAN").replace("Elevation", "Framing Plan")
            else:
                plan_title = f"{raw_title} - FRAMING PLAN"
        sec_beams = ()

    # Map nodes to absolute plan coordinates
    plan_coords: dict[Any, tuple[float, float]] = {}
    x_min_ref = 0.0
    y_min_ref = 0.0
    if isinstance(data, GeneralFrameData):
        if data.grid_x:
            x_min_ref = min(g.coord for g in data.grid_x)
        elif data.nodes:
            x_min_ref = min(n.x for n in data.nodes)
        if data.grid_y:
            y_min_ref = min(g.coord for g in data.grid_y)
        elif data.nodes:
            y_min_ref = min(n.y for n in data.nodes)
        for n in data.nodes:
            plan_coords[n.id] = (ox + (n.x - x_min_ref), oy + (n.y - y_min_ref))

    # Compute absolute grid line positions
    if isinstance(data, GeneralFrameData) and data.grid_x and data.grid_y:
        x_positions = [ox + (g.coord - x_min_ref) for g in data.grid_x]
        y_positions = [oy + (g.coord - y_min_ref) for g in data.grid_y]
    else:
        x_positions = [ox]
        for b in bays_x:
            x_positions.append(x_positions[-1] + b)

        y_positions = [oy]
        for b in bays_y:
            y_positions.append(y_positions[-1] + b)

    x_min, x_max = x_positions[0], x_positions[-1]
    y_min, y_max = y_positions[0], y_positions[-1]

    # Grid extensions:
    # At top and right, standard extension
    grid_ext_top = 900.0 if is_metric else 36.0
    grid_ext_right = 900.0 if is_metric else 36.0
    # At bottom and left, dimensions are at dim_offset * 1.5 and dim_offset * 2.5,
    # so grid lines extend past dimensions so bubbles never collide with dimension lines
    grid_ext_bot = dim_offset * 3.4
    grid_ext_left = dim_offset * 3.4

    # 1. Draw Grid Lines and Bubbles (X direction / Vertical lines)
    for i, x in enumerate(x_positions):
        label = labels_x[i] if i < len(labels_x) else chr(65 + i)
        # Vertical grid line extending past bottom dimensions up to top
        draw_line(target, (x, y_min - grid_ext_bot), (x, y_max + grid_ext_top), layer="GRID")
        # Top bubble
        top_center = (x, y_max + grid_ext_top + bubble_radius)
        draw_circle(target, top_center, bubble_radius, layer="GRID")
        draw_text(
            target,
            label,
            position=(top_center[0] - text_size * 0.35, top_center[1] - text_size * 0.35),
            height=text_size,
            layer="TEXT",
        )
        # Bottom bubble (placed cleanly past dimension lines)
        bot_center = (x, y_min - grid_ext_bot - bubble_radius)
        draw_circle(target, bot_center, bubble_radius, layer="GRID")
        draw_text(
            target,
            label,
            position=(bot_center[0] - text_size * 0.35, bot_center[1] - text_size * 0.35),
            height=text_size,
            layer="TEXT",
        )

    # 2. Draw Grid Lines and Bubbles (Y direction / Horizontal lines)
    for j, y in enumerate(y_positions):
        label = labels_y[j] if j < len(labels_y) else str(j + 1)
        # Horizontal grid line extending past left dimensions to right
        draw_line(target, (x_min - grid_ext_left, y), (x_max + grid_ext_right, y), layer="GRID")
        # Left bubble (placed cleanly past dimension lines)
        left_center = (x_min - grid_ext_left - bubble_radius, y)
        draw_circle(target, left_center, bubble_radius, layer="GRID")
        draw_text(
            target,
            label,
            position=(left_center[0] - text_size * 0.35, left_center[1] - text_size * 0.35),
            height=text_size,
            layer="TEXT",
        )
        # Right bubble
        right_center = (x_max + grid_ext_right + bubble_radius, y)
        draw_circle(target, right_center, bubble_radius, layer="GRID")
        draw_text(
            target,
            label,
            position=(right_center[0] - text_size * 0.35, right_center[1] - text_size * 0.35),
            height=text_size,
            layer="TEXT",
        )

    # Check if explicit members are available for realistic drawing
    has_member_beams = False
    has_member_cols = False
    if isinstance(data, GeneralFrameData) and data.members:
        has_member_beams = any(m.member_type.lower() in ("beam", "joist", "girder", "truss", "chord") for m in data.members)
        has_member_cols = any(m.member_type.lower() == "column" for m in data.members)

    # 3. Draw Beams
    if has_member_beams and isinstance(data, GeneralFrameData):
        for mem in data.members:
            m_type = mem.member_type.lower()
            if m_type not in ("beam", "joist", "girder", "truss", "chord"):
                continue
            p1 = plan_coords.get(mem.start_node)
            p2 = plan_coords.get(mem.end_node)
            if not p1 or not p2:
                continue
            x1, y1 = p1
            x2, y2 = p2
            dx = x2 - x1
            dy = y2 - y1
            L = math.hypot(dx, dy)
            if L <= 1e-3:
                continue
            bw = mem.width_in if mem.width_in > 0 else beam_w
            half_bw = bw / 2.0
            ux, uy = -dy / L, dx / L  # normal perpendicular to beam

            p1_left = (x1 + ux * half_bw, y1 + uy * half_bw)
            p2_left = (x2 + ux * half_bw, y2 + uy * half_bw)
            p1_right = (x1 - ux * half_bw, y1 - uy * half_bw)
            p2_right = (x2 - ux * half_bw, y2 - uy * half_bw)

            draw_line(target, p1_left, p2_left, layer="BEAM")
            draw_line(target, p1_right, p2_right, layer="BEAM")
            draw_line(target, (x1, y1), (x2, y2), layer="CENTERLINE")

            if mem.name and getattr(data, "show_member_tags", True):
                mid_x = (x1 + x2) / 2.0
                mid_y = (y1 + y2) / 2.0
                draw_text(
                    target,
                    mem.name,
                    position=(mid_x + ux * (half_bw + text_size * 0.2), mid_y + uy * (half_bw + text_size * 0.2)),
                    height=text_size * 0.75,
                    layer="TEXT",
                )
    else:
        # Fallback: Horizontal beams along Y grid lines
        half_bw = beam_w / 2.0
        for j, y in enumerate(y_positions):
            for i in range(len(bays_x)):
                x1 = x_positions[i] + col_w / 2.0
                x2 = x_positions[i + 1] - col_w / 2.0
                if x2 > x1:
                    draw_line(target, (x1, y + half_bw), (x2, y + half_bw), layer="BEAM")
                    draw_line(target, (x1, y - half_bw), (x2, y - half_bw), layer="BEAM")
                    b_name = f"B{i+1}"
                    draw_text(
                        target,
                        b_name,
                        position=((x1 + x2) / 2.0 - text_size * 0.6, y + half_bw + text_size * 0.3),
                        height=text_size * 0.75,
                        layer="TEXT",
                    )

        # Fallback: Vertical beams along X grid lines
        for i, x in enumerate(x_positions):
            for j in range(len(bays_y)):
                y1 = y_positions[j] + col_d / 2.0
                y2 = y_positions[j + 1] - col_d / 2.0
                if y2 > y1:
                    draw_line(target, (x - half_bw, y1), (x - half_bw, y2), layer="BEAM")
                    draw_line(target, (x + half_bw, y1), (x + half_bw, y2), layer="BEAM")
                    b_name = f"B{len(bays_x) + j + 1}"
                    draw_text(
                        target,
                        b_name,
                        position=(x + half_bw + text_size * 0.3, (y1 + y2) / 2.0 - text_size * 0.35),
                        height=text_size * 0.75,
                        layer="TEXT",
                    )

    # Optional secondary beams
    for bx_idx, by_idx, orient in sec_beams:
        if 0 <= bx_idx < len(bays_x) and 0 <= by_idx < len(bays_y):
            if orient == "mid_x":
                mid_x = (x_positions[bx_idx] + x_positions[bx_idx + 1]) / 2.0
                y1 = y_positions[by_idx] + half_bw
                y2 = y_positions[by_idx + 1] - half_bw
                draw_line(target, (mid_x - half_bw * 0.75, y1), (mid_x - half_bw * 0.75, y2), layer="BEAM")
                draw_line(target, (mid_x + half_bw * 0.75, y1), (mid_x + half_bw * 0.75, y2), layer="BEAM")
                draw_text(
                    target,
                    "SB",
                    position=(mid_x + half_bw, (y1 + y2) / 2.0),
                    height=text_size * 0.6,
                    layer="TEXT",
                )
            elif orient == "mid_y":
                mid_y = (y_positions[by_idx] + y_positions[by_idx + 1]) / 2.0
                x1 = x_positions[bx_idx] + half_bw
                x2 = x_positions[bx_idx + 1] - half_bw
                draw_line(target, (x1, mid_y - half_bw * 0.75), (x2, mid_y - half_bw * 0.75), layer="BEAM")
                draw_line(target, (x1, mid_y + half_bw * 0.75), (x2, mid_y + half_bw * 0.75), layer="BEAM")
                draw_text(
                    target,
                    "SB",
                    position=((x1 + x2) / 2.0, mid_y + half_bw),
                    height=text_size * 0.6,
                    layer="TEXT",
                )

    # 4. Draw Columns
    if has_member_cols and isinstance(data, GeneralFrameData):
        seen_cols = set()
        c_count = 1
        for mem in data.members:
            if mem.member_type.lower() != "column":
                continue
            p = plan_coords.get(mem.start_node) or plan_coords.get(mem.end_node)
            if not p:
                continue
            cx, cy = p
            pos_key = (round(cx, 1), round(cy, 1))
            if pos_key in seen_cols:
                continue
            seen_cols.add(pos_key)

            cw = mem.width_in if mem.width_in > 0 else col_w
            cd = mem.depth_in if mem.depth_in > 0 else col_d
            draw_rectangle(
                target,
                origin=(cx - cw / 2.0, cy - cd / 2.0),
                width=cw,
                height=cd,
                close=True,
                layer="COLUMN",
            )
            c_tag = mem.name or f"C{c_count}"
            if getattr(data, "show_member_tags", True):
                draw_text(
                    target,
                    c_tag,
                    position=(cx - cw * 0.4, cy - cd * 0.25),
                    height=text_size * 0.6,
                    layer="TEXT",
                )
            c_count += 1
    else:
        # Fallback: Grid Intersections
        c_count = 1
        for i, x in enumerate(x_positions):
            for j, y in enumerate(y_positions):
                draw_rectangle(
                    target,
                    origin=(x - col_w / 2.0, y - col_d / 2.0),
                    width=col_w,
                    height=col_d,
                    close=True,
                    layer="COLUMN",
                )
                c_tag = f"C{c_count}"
                draw_text(
                    target,
                    c_tag,
                    position=(x - col_w * 0.4, y - col_d * 0.25),
                    height=text_size * 0.6,
                    layer="TEXT",
                )
                c_count += 1

    # 5. Dimensions
    # dimstyle already configured above
    # Bottom X bay dimensions
    for i in range(len(bays_x)):
        x1 = x_positions[i]
        x2 = x_positions[i + 1]
        draw_dimension(
            target,
            (x1, y_min),
            (x2, y_min),
            location=((x1 + x2) / 2.0, y_min - dim_offset * 1.5),
            dimstyle=dimstyle,
        )
    # Overall X dimension
    draw_dimension(
        target,
        (x_min, y_min),
        (x_max, y_min),
        location=((x_min + x_max) / 2.0, y_min - dim_offset * 2.5),
        dimstyle=dimstyle,
    )

    # Left Y bay dimensions
    for j in range(len(bays_y)):
        y1 = y_positions[j]
        y2 = y_positions[j + 1]
        draw_dimension(
            target,
            (x_min, y1),
            (x_min, y2),
            location=(x_min - dim_offset * 1.5, (y1 + y2) / 2.0),
            dimstyle=dimstyle,
        )
    # Overall Y dimension
    draw_dimension(
        target,
        (x_min, y_min),
        (x_min, y_max),
        location=(x_min - dim_offset * 2.5, (y_min + y_max) / 2.0),
        dimstyle=dimstyle,
    )

    # 6. Title
    title_y = y_min - grid_ext_bot - bubble_radius * 2.0 - text_size * 2.0
    draw_text(
        target,
        plan_title.upper(),
        position=((x_min + x_max) / 2.0 - len(plan_title) * text_size * 0.3, title_y),
        height=text_size * 1.4,
        layer="TITLE",
    )
    draw_line(
        target,
        ((x_min + x_max) / 2.0 - len(plan_title) * text_size * 0.35, title_y - text_size * 0.3),
        ((x_min + x_max) / 2.0 + len(plan_title) * text_size * 0.35, title_y - text_size * 0.3),
        layer="TITLE",
    )

    return {
        "origin": (ox, oy),
        "bounding_box": (
            x_min - grid_ext_left - bubble_radius * 2.5,
            title_y - text_size * 1.5,
            x_max + grid_ext_right + bubble_radius * 2.5,
            y_max + grid_ext_top + bubble_radius * 2.5,
        ),
    }


# ---------------------------------------------------------------------------
# Frame Elevation View
# ---------------------------------------------------------------------------


def elevation_view(
    target: Any,
    data: FrameElevationData | GeneralFrameData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Draw a 2D structural frame elevation (columns, beams, braces, levels, grids, dimensions)."""
    ox, oy = origin
    scale = kwargs.get("scale", getattr(data, "scale", None))
    unit = kwargs.get("unit", getattr(data, "unit", None))
    is_metric = unit.is_metric if unit is not None else _detect_metric(data)

    if scale is not None or unit is not None:
        from struct_draw.core.units import DrawingScale, DrawingUnit, SCALE_1_50, SCALE_1_4_IN
        from struct_draw.style.annotation_config import DEFAULT_ANNOTATION_CONFIG
        d_unit = unit or (DrawingUnit.MM if is_metric else DrawingUnit.IN)
        d_scale = scale or (SCALE_1_50 if is_metric else SCALE_1_4_IN)
        text_size = DEFAULT_ANNOTATION_CONFIG.text_height(d_scale, d_unit)
        bubble_radius = DEFAULT_ANNOTATION_CONFIG.bubble_radius(d_scale, d_unit)
        dim_offset = DEFAULT_ANNOTATION_CONFIG.dim_offset(d_scale, d_unit)
        level_ext = dim_offset * 1.5
        dimstyle = "DIM_ELEV" if is_metric else "Linear"
    else:
        text_size = 200.0 if is_metric else 8.0
        bubble_radius = 250.0 if is_metric else 10.0
        dim_offset = 600.0 if is_metric else 24.0
        level_ext = 900.0 if is_metric else 36.0
        dimstyle = "Metric" if is_metric else "Linear"

    # Build node and member geometry
    if isinstance(data, FrameElevationData):
        bays = list(data.bays)
        heights = list(data.story_heights)
        col_w = data.col_width_in
        col_d = data.col_depth_in
        beam_w = data.beam_width_in
        beam_d = data.beam_depth_in
        grid_labels = list(data.grid_labels) if data.grid_labels else [chr(65 + i) for i in range(len(bays) + 1)]
        level_labels = list(data.level_labels) if data.level_labels else ["GL"] + [f"FL{i}" if i < len(heights) else "ROOF" for i in range(1, len(heights) + 1)]
        grid_suffix = f" ({data.grid_name})" if data.grid_name and data.grid_name not in data.title else ""
        elev_title = title or (f"{data.title}{grid_suffix}" if "ELEVATION" in data.title.upper() else f"{data.title}{grid_suffix} - ELEVATION")
        braced_bays = data.braced_bays

        # Convert to GeneralFrameData representation
        frame = GeneralFrameData.from_grid(
            name=data.name,
            bays=bays,
            story_heights=heights,
            col_width=col_w,
            col_depth=col_d,
            beam_width=beam_w,
            beam_depth=beam_d,
            grid_labels=grid_labels,
            level_labels=level_labels,
            braced_bays=braced_bays,
            title=elev_title,
            is_metric=is_metric,
        )
    else:
        frame = data
        if title:
            elev_title = title
        else:
            raw_title = getattr(data, "title", "STRUCTURAL FRAME")
            upper = raw_title.upper()
            if "ELEVATION & PLAN" in upper:
                elev_title = raw_title.replace("ELEVATION & PLAN", "FRAME ELEVATION").replace("Elevation & Plan", "Frame Elevation").replace("Elevation & plan", "Frame Elevation")
            elif "ELEVATION AND PLAN" in upper:
                elev_title = raw_title.replace("ELEVATION AND PLAN", "FRAME ELEVATION").replace("Elevation and Plan", "Frame Elevation")
            elif "ELEVATION" in upper and "PLAN" not in upper:
                elev_title = raw_title
            elif "PLAN" in upper and "ELEVATION" not in upper:
                elev_title = raw_title.replace("PLAN", "FRAME ELEVATION").replace("Plan", "Frame Elevation")
            else:
                elev_title = f"{raw_title} - FRAME ELEVATION"

    # Map nodes by ID
    node_coords: dict[Any, tuple[float, float]] = {}
    x_vals: list[float] = []
    y_vals: list[float] = []

    has_3d_z = any(abs(getattr(nd, "z", 0.0)) > 1e-4 for nd in frame.nodes)
    for n in frame.nodes:
        nx = ox + n.x
        ny = oy + (n.z if has_3d_z else n.y)
        node_coords[n.id] = (nx, ny)
        x_vals.append(nx)
        y_vals.append(ny)

    x_min = min(x_vals) if x_vals else ox
    x_max = max(x_vals) if x_vals else ox + 720.0
    y_min = min(y_vals) if y_vals else oy
    y_max = max(y_vals) if y_vals else oy + 360.0

    # 1. Draw Levels (Horizontal level lines with level markers/labels strictly on the RIGHT)
    if frame.levels:
        for lvl in frame.levels:
            ly = oy + lvl.elevation
            # Level line spanning from frame left to right extension
            draw_line(target, (x_min - dim_offset * 0.5, ly), (x_max + level_ext, ly), layer="LEVEL")
            # Level annotation symbol and text on RIGHT side only
            lvl_lbl = f"{lvl.label} (EL. {lvl.elevation:.0f})" if is_metric else f"{lvl.label} (EL. {lvl.elevation:.1f})"
            draw_level_marker(
                target,
                anchor=(x_max + level_ext, ly),
                direction="right",
                length=level_ext * 0.4,
                label=lvl_lbl,
                label_offset=(level_ext * 0.1, text_size * 0.3),
                text_height=text_size * 0.85,
            )

    # 2. Draw Grid Lines and Bubbles on top
    if frame.grid_x:
        for gx in frame.grid_x:
            gx_pos = ox + gx.coord
            draw_line(target, (gx_pos, y_min - dim_offset * 0.5), (gx_pos, y_max + level_ext), layer="GRID")
            top_c = (gx_pos, y_max + level_ext + bubble_radius)
            draw_circle(target, top_c, bubble_radius, layer="GRID")
            draw_text(
                target,
                gx.label,
                position=(top_c[0] - text_size * 0.35, top_c[1] - text_size * 0.35),
                height=text_size,
                layer="TEXT",
            )

    # 3. Draw Members (Columns, Beams, Braces, Trusses)
    for mem in frame.members:
        p1 = node_coords.get(mem.start_node, mem.start_node if isinstance(mem.start_node, tuple) else (ox, oy))
        p2 = node_coords.get(mem.end_node, mem.end_node if isinstance(mem.end_node, tuple) else (ox, oy))
        x1, y1 = p1
        x2, y2 = p2

        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length <= 1e-3:
            continue

        m_type = mem.member_type.lower()
        w = mem.width_in
        d = mem.depth_in

        if m_type == "column":
            # Vertical column outline box
            col_w = w
            cx = (x1 + x2) / 2.0
            draw_rectangle(
                target,
                origin=(cx - col_w / 2.0, min(y1, y2)),
                width=col_w,
                height=abs(y2 - y1),
                close=True,
                layer="COLUMN",
            )
            # Column centerline
            draw_line(target, (cx, min(y1, y2)), (cx, max(y1, y2)), layer="CENTERLINE")
            # Text tag
            if mem.name:
                draw_text(
                    target,
                    mem.name,
                    position=(cx + col_w * 0.6, (y1 + y2) / 2.0 - text_size * 0.35),
                    height=text_size * 0.75,
                    layer="TEXT",
                )

        elif m_type == "beam":
            # Horizontal beam outline box (drawn below the floor node line by beam depth)
            beam_d = d
            by = max(y1, y2)
            draw_rectangle(
                target,
                origin=(min(x1, x2), by - beam_d),
                width=abs(x2 - x1),
                height=beam_d,
                close=True,
                layer="BEAM",
            )
            # Centerline
            draw_line(target, (x1, by - beam_d / 2.0), (x2, by - beam_d / 2.0), layer="CENTERLINE")
            # Text tag
            if mem.name:
                draw_text(
                    target,
                    mem.name,
                    position=((x1 + x2) / 2.0 - text_size * 0.8, by - beam_d / 2.0 - text_size * 0.35),
                    height=text_size * 0.75,
                    layer="TEXT",
                )

        else:
            # Diagonal brace, truss member, strut or arbitrary angle
            # Draw double outline along direction vector with depth d
            half_d = d / 2.0
            ux, uy = -dy / length, dx / length  # perpendicular normal
            poly_pts = [
                (x1 + ux * half_d, y1 + uy * half_d),
                (x2 + ux * half_d, y2 + uy * half_d),
                (x2 - ux * half_d, y2 - uy * half_d),
                (x1 - ux * half_d, y1 - uy * half_d),
            ]
            draw_polyline(target, poly_pts, close=True, layer="CONC_OUTLINE")
            draw_line(target, (x1, y1), (x2, y2), layer="CENTERLINE")
            if mem.name:
                draw_text(
                    target,
                    mem.name,
                    position=((x1 + x2) / 2.0 + ux * d, (y1 + y2) / 2.0 + uy * d),
                    height=text_size * 0.7,
                    layer="TEXT",
                )

    # dimstyle already configured above

    # Story height dimensions on the LEFT side
    if frame.levels and len(frame.levels) >= 2:
        for j in range(len(frame.levels) - 1):
            ly1 = oy + frame.levels[j].elevation
            ly2 = oy + frame.levels[j + 1].elevation
            draw_dimension(
                target,
                (x_min, ly1),
                (x_min, ly2),
                location=(x_min - dim_offset * 1.5, (ly1 + ly2) / 2.0),
                dimstyle=dimstyle,
            )
        # Total frame height dimension on the LEFT side
        draw_dimension(
            target,
            (x_min, y_min),
            (x_min, y_max),
            location=(x_min - dim_offset * 2.5, (y_min + y_max) / 2.0),
            dimstyle=dimstyle,
        )

    # Bay width dimensions at the bottom
    if frame.grid_x and len(frame.grid_x) >= 2:
        for i in range(len(frame.grid_x) - 1):
            gx1 = ox + frame.grid_x[i].coord
            gx2 = ox + frame.grid_x[i + 1].coord
            draw_dimension(
                target,
                (gx1, y_min),
                (gx2, y_min),
                location=((gx1 + gx2) / 2.0, y_min - dim_offset * 1.3),
                dimstyle=dimstyle,
            )
        # Overall frame width dimension
        draw_dimension(
            target,
            (x_min, y_min),
            (x_max, y_min),
            location=((x_min + x_max) / 2.0, y_min - dim_offset * 2.3),
            dimstyle=dimstyle,
        )

    # 5. Title
    title_y = y_min - dim_offset * 3.4
    draw_text(
        target,
        elev_title.upper(),
        position=((x_min + x_max) / 2.0 - len(elev_title) * text_size * 0.3, title_y),
        height=text_size * 1.4,
        layer="TITLE",
    )
    draw_line(
        target,
        ((x_min + x_max) / 2.0 - len(elev_title) * text_size * 0.35, title_y - text_size * 0.3),
        ((x_min + x_max) / 2.0 + len(elev_title) * text_size * 0.35, title_y - text_size * 0.3),
        layer="TITLE",
    )

    return {
        "origin": (ox, oy),
        "bounding_box": (
            x_min - dim_offset * 3.8,
            title_y - text_size * 1.5,
            x_max + level_ext + 2500.0,
            y_max + level_ext + bubble_radius * 2.5,
        ),
    }


# ---------------------------------------------------------------------------
# Truss Outline & Elevation View
# ---------------------------------------------------------------------------


def truss_view(
    target: Any,
    data: TrussData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    title: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Draw a roof or bridge truss outline view without rebar (Pratt, Howe, Warren, Pitched)."""
    ox, oy = origin
    scale = kwargs.get("scale", getattr(data, "scale", None))
    unit = kwargs.get("unit", getattr(data, "unit", None))
    is_metric = unit.is_metric if unit is not None else data.is_metric

    span = data.span_in
    height = data.height_in
    num_panels = max(2, data.panels)
    panel_w = span / num_panels
    t_type = data.truss_type.lower()
    c_depth = data.chord_depth_in
    w_depth = data.web_depth_in

    if scale is not None or unit is not None:
        from struct_draw.core.units import DrawingScale, DrawingUnit, SCALE_1_50, SCALE_1_4_IN
        from struct_draw.style.annotation_config import DEFAULT_ANNOTATION_CONFIG
        d_unit = unit or (DrawingUnit.MM if is_metric else DrawingUnit.IN)
        d_scale = scale or (SCALE_1_50 if is_metric else SCALE_1_4_IN)
        text_size = DEFAULT_ANNOTATION_CONFIG.text_height(d_scale, d_unit)
        dim_offset = DEFAULT_ANNOTATION_CONFIG.dim_offset(d_scale, d_unit)
        dimstyle = "DIM_ELEV" if is_metric else "Linear"
    else:
        text_size = 200.0 if is_metric else 8.0
        dim_offset = 500.0 if is_metric else 20.0
        dimstyle = "Metric" if is_metric else "Linear"
    truss_title = title or data.title

    # Generate Bottom & Top chord nodes
    bot_nodes: list[tuple[float, float]] = []
    top_nodes: list[tuple[float, float]] = []

    for i in range(num_panels + 1):
        x = ox + i * panel_w
        bot_nodes.append((x, oy))

        if t_type in ("pitched", "fink", "howe_pitched", "pratt_pitched"):
            # Pitched roof truss: ridge at center (span / 2)
            mid = num_panels / 2.0
            dist_from_center = abs(i - mid) / mid
            y = oy + height * (1.0 - dist_from_center)
            top_nodes.append((x, y))
        else:
            # Parallel chord truss (Pratt, Howe, Warren)
            top_nodes.append((x, oy + height))

    # 1. Draw Bottom Chord (Continuous double line / rectangular profile)
    draw_rectangle(
        target,
        origin=(ox, oy - c_depth),
        width=span,
        height=c_depth,
        close=True,
        layer="BEAM",
    )
    draw_line(target, (ox, oy - c_depth / 2.0), (ox + span, oy - c_depth / 2.0), layer="CENTERLINE")
    draw_text(
        target,
        "BOTTOM CHORD",
        position=(ox + span / 2.0 - text_size * 3.0, oy - c_depth * 1.5 - text_size * 0.5),
        height=text_size * 0.8,
        layer="TEXT",
    )

    # 2. Draw Top Chord
    if t_type in ("pitched", "fink", "howe_pitched", "pratt_pitched"):
        # Pitched top chord (two sloped legs meeting at ridge)
        mid_idx = num_panels // 2
        # Left rafter
        p_left_start = top_nodes[0]
        p_ridge = top_nodes[mid_idx]
        p_right_end = top_nodes[-1]
        _draw_angled_member(target, p_left_start, p_ridge, depth=c_depth, layer="BEAM")
        _draw_angled_member(target, p_ridge, p_right_end, depth=c_depth, layer="BEAM")
        draw_text(
            target,
            "TOP CHORD / RAFTER",
            position=(ox + span * 0.25, oy + height * 0.6 + c_depth),
            height=text_size * 0.8,
            layer="TEXT",
        )
    else:
        # Parallel top chord
        draw_rectangle(
            target,
            origin=(ox, oy + height),
            width=span,
            height=c_depth,
            close=True,
            layer="BEAM",
        )
        draw_line(target, (ox, oy + height + c_depth / 2.0), (ox + span, oy + height + c_depth / 2.0), layer="CENTERLINE")
        draw_text(
            target,
            "TOP CHORD",
            position=(ox + span / 2.0 - text_size * 2.5, oy + height + c_depth * 1.2),
            height=text_size * 0.8,
            layer="TEXT",
        )

    # 3. Draw Web Members (Verticals + Diagonals)
    # Verticals
    for i in range(num_panels + 1):
        bp = bot_nodes[i]
        tp = top_nodes[i]
        v_len = tp[1] - bp[1]
        if v_len > 1.0:
            draw_rectangle(
                target,
                origin=(bp[0] - w_depth / 2.0, bp[1]),
                width=w_depth,
                height=v_len,
                close=True,
                layer="COLUMN",
            )
            draw_line(target, bp, tp, layer="CENTERLINE")

    # Diagonals depending on truss type
    mid = num_panels / 2.0
    for i in range(num_panels):
        if t_type == "warren":
            # Alternating zig-zag
            if i % 2 == 0:
                _draw_angled_member(target, bot_nodes[i], top_nodes[i + 1], depth=w_depth, layer="CONC_OUTLINE")
            else:
                _draw_angled_member(target, top_nodes[i], bot_nodes[i + 1], depth=w_depth, layer="CONC_OUTLINE")
        elif t_type in ("howe", "howe_pitched"):
            # Diagonals sloped away from center (compression diagonals)
            if i < mid:
                _draw_angled_member(target, bot_nodes[i], top_nodes[i + 1], depth=w_depth, layer="CONC_OUTLINE")
            else:
                _draw_angled_member(target, top_nodes[i], bot_nodes[i + 1], depth=w_depth, layer="CONC_OUTLINE")
        else:
            # Pratt (default): diagonals sloped toward center (tension diagonals)
            if i < mid:
                _draw_angled_member(target, top_nodes[i], bot_nodes[i + 1], depth=w_depth, layer="CONC_OUTLINE")
            else:
                _draw_angled_member(target, bot_nodes[i], top_nodes[i + 1], depth=w_depth, layer="CONC_OUTLINE")

    # dimstyle already configured above

    # Bottom panel dimensions
    for i in range(num_panels):
        x1 = bot_nodes[i][0]
        x2 = bot_nodes[i + 1][0]
        draw_dimension(
            target,
            (x1, oy - c_depth),
            (x2, oy - c_depth),
            location=((x1 + x2) / 2.0, oy - c_depth - dim_offset),
            dimstyle=dimstyle,
        )

    # Overall span dimension
    draw_dimension(
        target,
        (ox, oy - c_depth),
        (ox + span, oy - c_depth),
        location=(ox + span / 2.0, oy - c_depth - dim_offset * 1.8),
        dimstyle=dimstyle,
    )

    # Truss height dimension on the right
    draw_dimension(
        target,
        (ox + span, oy),
        (ox + span, oy + height),
        location=(ox + span + dim_offset * 1.5, oy + height / 2.0),
        dimstyle=dimstyle,
    )

    # 5. Title
    title_y = oy - c_depth - dim_offset * 2.8
    draw_text(
        target,
        truss_title.upper(),
        position=(ox + span / 2.0 - len(truss_title) * text_size * 0.3, title_y),
        height=text_size * 1.4,
        layer="TITLE",
    )
    draw_line(
        target,
        (ox + span / 2.0 - len(truss_title) * text_size * 0.35, title_y - text_size * 0.3),
        (ox + span / 2.0 + len(truss_title) * text_size * 0.35, title_y - text_size * 0.3),
        layer="TITLE",
    )

    return {
        "origin": (ox, oy),
        "bounding_box": (ox - dim_offset, oy - dim_offset * 3.5, ox + span + dim_offset * 2.5, oy + height + c_depth * 2),
    }


def drawing(
    target: Any,
    data: GeneralFrameData | FramingPlanData | FrameElevationData | TrussData,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
) -> dict[str, Any]:
    """Render the general drawing based on the data type and configured view mode."""
    if isinstance(data, FramingPlanData):
        return plan_view(target, data, origin=origin)
    elif isinstance(data, FrameElevationData):
        return elevation_view(target, data, origin=origin)
    elif isinstance(data, TrussData):
        return truss_view(target, data, origin=origin)
    elif isinstance(data, GeneralFrameData):
        if data.view_mode == "plan":
            return plan_view(target, data, origin=origin)
        elif data.view_mode == "truss":
            truss_d = TrussData(name=data.name, span_in=data.nodes[-1].x if data.nodes else 480.0, height_in=data.levels[-1].elevation if data.levels else 96.0, title=data.title, is_metric=data.is_metric)
            return truss_view(target, truss_d, origin=origin)
        elif data.view_mode == "both":
            # Layout plan on top and elevation dynamically below using bounding box
            res_plan = plan_view(target, data, origin=origin)
            plan_bbox = res_plan.get("bounding_box", (origin[0], origin[1], origin[0] + 500.0, origin[1] + 500.0))
            is_m = _detect_metric(data)
            margin = 3000.0 if is_m else 120.0

            # Calculate elevation height to place it cleanly below plan_bbox[1] (min_y)
            if data.levels:
                elev_height = max(l.elevation for l in data.levels) - min(l.elevation for l in data.levels)
            elif data.nodes:
                y_nodes = [n.y for n in data.nodes]
                elev_height = max(y_nodes) - min(y_nodes)
            else:
                elev_height = 10000.0 if is_m else 360.0

            # Extra margin for elevation dimensions and grid bubbles on top of elevation
            top_headroom = 1500.0 if is_m else 60.0
            elev_y = plan_bbox[1] - margin - elev_height - top_headroom
            elev_origin = (origin[0], elev_y)

            res_elev = elevation_view(target, data, origin=elev_origin)
            return {"plan": res_plan, "elevation": res_elev}
        else:
            return elevation_view(target, data, origin=origin)
    else:
        return elevation_view(target, data, origin=origin)


# ---------------------------------------------------------------------------
# Internal Helper
# ---------------------------------------------------------------------------


def _draw_angled_member(
    target: Any,
    p1: tuple[float, float],
    p2: tuple[float, float],
    *,
    depth: float,
    layer: str = "CONC_OUTLINE",
) -> None:
    """Draw a double-line rectangular polygon for an angled truss member."""
    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1
    L = math.hypot(dx, dy)
    if L <= 1e-3:
        return
    ux, uy = -dy / L, dx / L
    half_d = depth / 2.0
    pts = [
        (x1 + ux * half_d, y1 + uy * half_d),
        (x2 + ux * half_d, y2 + uy * half_d),
        (x2 - ux * half_d, y2 - uy * half_d),
        (x1 - ux * half_d, y1 - uy * half_d),
    ]
    draw_polyline(target, pts, close=True, layer=layer)
    draw_line(target, (x1, y1), (x2, y2), layer="CENTERLINE")


__all__ = [
    "plan_view",
    "elevation_view",
    "truss_view",
    "drawing",
]
