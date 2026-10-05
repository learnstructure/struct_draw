"""struct_draw.core.primitives — Direct DXF primitives.

These are the **lowest** drawing-side functions in the package.
They wrap ezdxf's ``add_*`` methods with consistent signatures
that take the target layout (typically ``doc.modelspace()``) plus
explicit keyword arguments and emit the resulting DXF entity.

Composite drawing functions (:mod:`struct_draw.core.composite`)
are built on top of these. Element functions (``elements/``) are
built on top of the composite helpers. Adapters never call
primitives directly — adapters only translate data.
"""

from __future__ import annotations

from typing import Any, Sequence

from struct_draw.utils.exceptions import DrawError


# ---------------------------------------------------------------------------
# Basic entities
# ---------------------------------------------------------------------------


def draw_line(target: Any, start: tuple[float, float], end: tuple[float, float], *, layer: str = "0") -> Any:
    """Draw a line segment on ``target`` (a modelspace or block)."""
    return target.add_line(start, end, dxfattribs={"layer": layer})


def draw_polyline(
    target: Any,
    points: Sequence[tuple[float, float]],
    *,
    close: bool = False,
    layer: str = "0",
) -> Any:
    """Draw a lightweight polyline on ``target``."""
    if not points:
        raise DrawError("draw_polyline requires at least one point.")
    return target.add_lwpolyline(list(points), close=close, dxfattribs={"layer": layer})


def draw_rectangle(
    target: Any,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    width: float,
    height: float,
    close: bool = True,
    layer: str = "CONC_OUTLINE",
) -> Any:
    """Draw a closed rectangle of given ``width`` x ``height`` from ``origin``."""
    if width <= 0 or height <= 0:
        raise DrawError("draw_rectangle requires positive width and height.")
    x0, y0 = origin
    pts = [
        (x0, y0),
        (x0 + width, y0),
        (x0 + width, y0 + height),
        (x0, y0 + height),
        (x0, y0),
    ]
    return draw_polyline(target, pts, close=close, layer=layer)


def draw_circle(
    target: Any,
    center: tuple[float, float],
    radius: float,
    *,
    layer: str = "0",
) -> Any:
    """Draw a circle on ``target``."""
    if radius <= 0:
        raise DrawError("draw_circle requires a positive radius.")
    return target.add_circle(center, radius, dxfattribs={"layer": layer})


def draw_arc(
    target: Any,
    center: tuple[float, float],
    radius: float,
    start_angle: float,
    end_angle: float,
    *,
    layer: str = "0",
) -> Any:
    """Draw an arc on ``target`` (angles in degrees)."""
    if radius <= 0:
        raise DrawError("draw_arc requires a positive radius.")
    return target.add_arc(center, radius, start_angle, end_angle, dxfattribs={"layer": layer})


def draw_ellipse(
    target: Any,
    center: tuple[float, float],
    major_axis: tuple[float, float],
    *,
    ratio: float = 1.0,
    layer: str = "0",
) -> Any:
    """Draw an ellipse on ``target``.

    ``major_axis`` is the vector from the center to one end of
    the major axis (in drawing units). ``ratio`` is the
    minor/major ratio (must be in (0, 1]).
    """
    if not (0 < ratio <= 1):
        raise DrawError("draw_ellipse requires 0 < ratio <= 1.")
    return target.add_ellipse(center, major_axis, ratio, dxfattribs={"layer": layer})


# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------


def draw_text(
    target: Any,
    text: str,
    *,
    position: tuple[float, float],
    height: float = 0.10,
    rotation: float = 0.0,
    style: str | None = None,
    layer: str = "TEXT",
    align: Any | None = None,
) -> Any:
    """Draw a single-line TEXT entity or MTEXT entity if text contains line breaks."""
    if not text:
        raise DrawError("draw_text requires non-empty text.")
    if "\n" in text:
        return draw_mtext(
            target, text, position=position, height=height, style=style, layer=layer
        )
    attribs: dict[str, Any] = {"layer": layer, "height": height, "rotation": rotation}
    if style:
        attribs["style"] = style
    entity = target.add_text(text, dxfattribs={"insert": position, **attribs})
    if align is not None and hasattr(entity, "set_placement"):
        try:
            from ezdxf.enums import TextEntityAlignment
            if isinstance(align, str):
                align_enum = getattr(TextEntityAlignment, align.upper(), None)
                if align_enum is not None:
                    entity.set_placement(position, align=align_enum)
            else:
                entity.set_placement(position, align=align)
        except Exception:
            pass
    return entity


def draw_mtext(
    target: Any,
    text: str,
    *,
    position: tuple[float, float],
    width: float = 0.0,
    height: float = 0.10,
    style: str | None = None,
    layer: str = "TEXT",
) -> Any:
    """Draw an MTEXT (multi-line text) entity."""
    if not text:
        raise DrawError("draw_mtext requires non-empty text.")
    if not hasattr(target, "add_mtext"):
        attribs: dict[str, Any] = {"layer": layer, "height": height}
        if style:
            attribs["style"] = style
        return target.add_text(text, dxfattribs={"insert": position, **attribs})

    attribs: dict[str, Any] = {"layer": layer, "char_height": height}
    if style:
        attribs["style"] = style
    mtext = target.add_mtext(text, dxfattribs=attribs)
    if hasattr(mtext, "set_location"):
        mtext.set_location(position)
    if width > 0 and hasattr(mtext, "dxf"):
        mtext.dxf.width = width
    return mtext


# ---------------------------------------------------------------------------
# Hatching
# ---------------------------------------------------------------------------


def draw_hatch(
    target: Any,
    *,
    paths: Sequence[dict[str, Any]],
    pattern: str = "ANSI31",
    scale: float = 1.0,
    layer: str = "HATCH",
) -> Any:
    """Draw a hatch with one or more boundary paths.

    Each ``paths`` entry must contain ``{"type": "polyline" | "circle",
    ...}``. For ``"polyline"`` entries, ``"points"`` and optional
    ``"close"`` are required. For ``"circle"`` entries,
    ``"center"`` and ``"radius"`` are required.
    """
    hatch = target.add_hatch(dxfattribs={"layer": layer})
    for path in paths:
        if path["type"] == "polyline":
            is_closed = path.get("is_closed", path.get("close", True))
            hatch.paths.add_polyline_path(
                path["points"], is_closed=is_closed
            )
        elif path["type"] == "circle":
            hatch.paths.add_circle(path["center"], path["radius"])
        else:
            raise DrawError(f"Unknown hatch path type: {path['type']!r}")
    hatch.set_pattern_fill(pattern, scale=scale)
    return hatch


# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------


def draw_dim_linear(
    target: Any,
    p1: tuple[float, float],
    p2: tuple[float, float],
    location: tuple[float, float],
    *,
    text_override: str | None = None,
    dimstyle: str = "Linear",
    layer: str = "DIM_LINEAR",
) -> Any:
    """Draw a linear dimension (horizontal or vertical) between ``p1`` and ``p2``."""
    angle = 90.0 if abs(p1[0] - p2[0]) < 1e-6 else 0.0
    try:
        dim = target.add_linear_dim(
            base=location,
            p1=p1,
            p2=p2,
            angle=angle,
            dimstyle=dimstyle,
            dxfattribs={"layer": layer},
        )
    except TypeError:
        dim = target.add_linear_dim(
            p1, p2, location,
            angle=angle,
            dimstyle=dimstyle,
            dxfattribs={"layer": layer},
        )
    if text_override is not None:
        dim.set_text(text_override)
    if hasattr(dim, "render"):
        try:
            dim.render()
        except Exception:
            pass
    return dim


def draw_dim_aligned(
    target: Any,
    p1: tuple[float, float],
    p2: tuple[float, float],
    location: tuple[float, float],
    *,
    text_override: str | None = None,
    dimstyle: str = "Linear",
    layer: str = "DIM_LINEAR",
) -> Any:
    """Draw an aligned (parallel) dimension between ``p1`` and ``p2``."""
    dim = target.add_aligned_dim(
        base=location,
        p1=p1,
        p2=p2,
        dimstyle=dimstyle,
        dxfattribs={"layer": layer},
    )
    if text_override is not None:
        dim.set_text(text_override)
    if hasattr(dim, "render"):
        try:
            dim.render()
        except Exception:
            pass
    return dim


def draw_dim_angular(
    target: Any,
    center: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    location: tuple[float, float],
    *,
    dimstyle: str = "Angular",
    layer: str = "DIM_ANGULAR",
) -> Any:
    """Draw an angular dimension with vertex at ``center``."""
    return target.add_angular_dim(
        base=(center, p1, p2),
        location=location,
        dimstyle=dimstyle,
        dxfattribs={"layer": layer},
    )


def draw_dim_radial(
    target: Any,
    center: tuple[float, float],
    radius_point: tuple[float, float],
    *,
    radius: float | None = None,
    dimstyle: str = "Radial",
    layer: str = "DIM_RADIAL",
) -> Any:
    """Draw a radial (radius) dimension."""
    kwargs: dict[str, Any] = {
        "dimstyle": dimstyle,
        "dxfattribs": {"layer": layer},
    }
    if radius is not None:
        kwargs["radius"] = radius
    return target.add_radius_dim(center=center, radius=radius_point, **kwargs)


# ---------------------------------------------------------------------------
# Leader
# ---------------------------------------------------------------------------


def draw_leader(
    target: Any,
    vertices: Sequence[tuple[float, float]],
    text: str = "",
    *,
    arrow_size: float = 0.10,
    text_height: float = 0.20,
    layer: str = "LEADER",
) -> Any:
    """Draw an AutoCAD MULTILEADER (mLeader) entity with integrated multi-line MTEXT annotation,
    or an AutoCAD LEADER attached with MTEXT.
    """
    if len(vertices) < 2:
        raise DrawError("draw_leader requires at least two vertices.")

    clean_t = text.replace("φ", "mm dia").replace("Φ", "mm dia").replace("ϕ", "mm dia") if text else ""

    p0 = vertices[0]
    p1 = vertices[1]

    # Determine horizontal shelf parameters
    if len(vertices) >= 3:
        p_shelf = vertices[-1]
        landing_len = abs(p_shelf[0] - p1[0])
        if landing_len < 1e-3:
            landing_len = text_height * 2.5
        is_right = (p_shelf[0] >= p1[0])
    else:
        is_right = (p1[0] >= p0[0])
        landing_len = text_height * 2.5

    actual_arrow_size = arrow_size
    if actual_arrow_size <= 0.20 and text_height > 1.0:
        actual_arrow_size = text_height * 0.75
    elif actual_arrow_size <= 0.0:
        actual_arrow_size = text_height * 0.75

    # 1. Try AutoCAD native MULTILEADER (mLeader) via ezdxf MultiLeaderBuilder
    if clean_t and hasattr(target, "add_multileader_mtext"):
        try:
            from ezdxf.math import Vec2
            from ezdxf.render import mleader

            target_pt = Vec2(p0)
            elbow_pt = Vec2(p1)

            side = mleader.ConnectionSide.left if is_right else mleader.ConnectionSide.right
            align = mleader.TextAlignment.left if is_right else mleader.TextAlignment.right
            conn_type = mleader.HorizontalConnection.middle_of_top_line

            ml_builder = target.add_multileader_mtext("Standard")
            if hasattr(ml_builder, "multileader") and hasattr(ml_builder.multileader, "dxf"):
                ml_builder.multileader.dxf.layer = layer

            ml_builder.set_content(
                clean_t,
                char_height=text_height,
                alignment=align,
            )
            landing_gap = max(text_height * 0.15, 2.0 if text_height > 10.0 else 0.05)
            ml_builder.set_connection_properties(dogleg_length=landing_len, landing_gap=landing_gap)
            if actual_arrow_size > 0:
                try:
                    ml_builder.set_arrow_properties(size=actual_arrow_size)
                except Exception:
                    pass
            ml_builder.set_connection_types(left=conn_type, right=conn_type)

            cbox = ml_builder._build_connection_box()
            move_y = -cbox.left.y if is_right else -cbox.right.y
            dogleg_dir = mleader.DOGLEG_DIRECTIONS[side]
            last_seg = dogleg_dir * (landing_len + landing_gap)
            insert_pt = elbow_pt + last_seg + Vec2(0.0, move_y)

            ml_builder.add_leader_line(side, [target_pt])
            ml_builder.build(insert_pt)
            return ml_builder.multileader
        except Exception:
            pass

    # 2. Try AutoCAD LEADER object with attached MTEXT
    shelf_dx = landing_len if is_right else -landing_len
    p2 = (p1[0] + shelf_dx, p1[1])
    full_verts = [p0, p1, p2]

    leader = None
    if hasattr(target, "add_leader"):
        try:
            leader = target.add_leader(vertices=full_verts, dxfattribs={"layer": layer})
            if actual_arrow_size and hasattr(leader, "dxf") and hasattr(leader.dxf, "arrow_size"):
                try:
                    leader.dxf.arrow_size = actual_arrow_size
                except Exception:
                    pass
        except Exception:
            leader = draw_polyline(target, full_verts, close=False, layer=layer)
    else:
        leader = draw_polyline(target, full_verts, close=False, layer=layer)

    # 3. Add single multi-line MTEXT object
    if clean_t:
        text_gap = text_height * 0.25
        text_pos = (p2[0] + text_gap, p2[1]) if is_right else (p2[0] - text_gap, p2[1])
        if hasattr(target, "add_mtext"):
            draw_mtext(target, clean_t, position=text_pos, height=text_height, layer="TEXT")
        else:
            draw_text(target, clean_t, position=text_pos, height=text_height, layer="TEXT")

    return leader



# ---------------------------------------------------------------------------
# Block reference
# ---------------------------------------------------------------------------


def draw_blockref(
    target: Any,
    block_name: str,
    position: tuple[float, float],
    *,
    xscale: float = 1.0,
    yscale: float = 1.0,
    rotation: float = 0.0,
    layer: str = "0",
) -> Any:
    """Insert a block reference into ``target``."""
    return target.add_blockref(
        block_name,
        position,
        dxfattribs={
            "layer": layer,
            "xscale": xscale,
            "yscale": yscale,
            "rotation": rotation,
        },
    )


__all__ = [
    "draw_line",
    "draw_polyline",
    "draw_rectangle",
    "draw_circle",
    "draw_arc",
    "draw_ellipse",
    "draw_text",
    "draw_mtext",
    "draw_hatch",
    "draw_dim_linear",
    "draw_dim_aligned",
    "draw_dim_angular",
    "draw_dim_radial",
    "draw_leader",
    "draw_blockref",
]