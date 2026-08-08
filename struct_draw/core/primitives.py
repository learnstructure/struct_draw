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
) -> Any:
    """Draw a single-line TEXT entity."""
    if not text:
        raise DrawError("draw_text requires non-empty text.")
    attribs: dict[str, Any] = {"layer": layer, "height": height, "rotation": rotation}
    if style:
        attribs["style"] = style
    return target.add_text(text, dxfattribs={"insert": position, **attribs})


def draw_mtext(
    target: Any,
    text: str,
    *,
    position: tuple[float, float],
    width: float = 4.0,
    height: float = 0.10,
    style: str | None = None,
    layer: str = "TEXT",
) -> Any:
    """Draw an MTEXT (multi-line text) entity."""
    if not text:
        raise DrawError("draw_mtext requires non-empty text.")
    attribs: dict[str, Any] = {"layer": layer}
    if style:
        attribs["style"] = style
    mtext = target.add_mtext(text, dxfattribs=attribs)
    mtext.set_location(position, leader=False)
    if height:
        mtext.dxf.char_height = height
    if width:
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
    """Draw a multi-vertex leader with optional annotation text."""
    if len(vertices) < 2:
        raise DrawError("draw_leader requires at least two vertices.")
    leader = target.add_leader(vertices=list(vertices), dxfattribs={"layer": layer})
    if arrow_size and hasattr(leader, "dxf") and hasattr(leader.dxf, "arrow_size"):
        try:
            leader.dxf.arrow_size = arrow_size
        except Exception:
            pass
    if text:
        last_pt = vertices[-1]
        text_pos = (last_pt[0] + text_height * 0.5, last_pt[1])
        draw_text(target, text, position=text_pos, height=text_height, layer=layer)
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