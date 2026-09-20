"""struct_draw.core.stirrup — Professional double-line Stirrup / Tie drawing classes & helpers.

Provides geometry models and drawing generators for:
- Rectangular closed stirrups / ties (with double-line outer/inner faces and 135° seismic hooks or 90° hooks)
- Circular ties / spirals
- Intermediate supplementary crossties / interior hoops
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Sequence

from struct_draw.core.primitives import draw_circle, draw_line, draw_polyline


@dataclass
class StirrupGeometry:
    """Parametric model for rectangular or circular cross-section stirrup / tie reinforcement.

    Attributes
    ----------
    diameter : float
        Bar diameter of the stirrup (e.g. 0.375 for #3 tie, 10.0 for 10mm tie).
    width : float
        Out-to-out width of the stirrup rectangle (concrete_width - 2 * cover).
    depth : float
        Out-to-out depth / height of the stirrup rectangle (concrete_depth - 2 * cover).
    origin : tuple[float, float]
        Bottom-left coordinate (x0, y0) of the outer stirrup perimeter.
    hook_length : float | None
        Extension length of the hook past the bend (default: max(6 * diameter, 3.0 in / 75 mm)).
    hook_corner : str
        Corner where 135° seismic hooks are located: "top_left", "top_right", "bottom_left", "bottom_right".
    hook_angle_deg : float
        Hook angle (default: 135.0 degrees for seismic hooks).
    is_circular : bool
        True if stirrup is circular (e.g. for circular columns).
    circular_diameter : float
        Out-to-out diameter if circular.
    bend_radius : float | None
        Internal corner bend radius (default: 2 * diameter per ACI 318).
    double_line : bool
        If True, draws both outer and inner perimeter lines showing real tie thickness.
    layer : str
        CAD layer name (default: "STIRRUP").
    """

    diameter: float
    width: float
    depth: float
    origin: tuple[float, float] = (0.0, 0.0)
    hook_length: float | None = None
    hook_corner: str = "top_left"
    hook_angle_deg: float = 135.0
    is_circular: bool = False
    circular_diameter: float = 0.0
    bend_radius: float | None = None
    double_line: bool = True
    layer: str = "STIRRUP"

    @property
    def effective_hook_length(self) -> float:
        if self.hook_length is not None and self.hook_length > 0:
            return self.hook_length
        is_metric = self.width >= 100.0 or self.depth >= 100.0 or self.diameter >= 5.0
        return max(6.0 * self.diameter, 75.0 if is_metric else 3.0)

    def draw(self, target: Any) -> list[Any]:
        """Draw the stirrup (double-line or single-line) with standard 135° seismic hooks."""
        if self.is_circular:
            return self._draw_circular(target)
        return self._draw_rectangular(target)

    def _draw_circular(self, target: Any) -> list[Any]:
        out: list[Any] = []
        cx, cy = self.origin
        r_outer = (self.circular_diameter if self.circular_diameter > 0 else self.width) / 2.0
        c1 = draw_circle(target, (cx, cy), radius=r_outer, layer=self.layer)
        if c1:
            out.append(c1)
        if self.double_line and self.diameter > 0 and r_outer > self.diameter:
            c2 = draw_circle(target, (cx, cy), radius=r_outer - self.diameter, layer=self.layer)
            if c2:
                out.append(c2)
        return out

    def _draw_rectangular(self, target: Any) -> list[Any]:
        if self.width <= 0 or self.depth <= 0:
            return []

        out: list[Any] = []
        x0, y0 = self.origin
        w, d = self.width, self.depth
        t = max(0.01, self.diameter)

        # 1. Outer closed rectangle
        pts_outer = [
            (x0, y0),
            (x0 + w, y0),
            (x0 + w, y0 + d),
            (x0, y0 + d),
            (x0, y0),
        ]
        poly_outer = draw_polyline(target, pts_outer, close=True, layer=self.layer)
        if poly_outer:
            out.append(poly_outer)

        # 2. Inner rectangle (Double Line) if requested
        if self.double_line and w > 2.0 * t and d > 2.0 * t:
            pts_inner = [
                (x0 + t, y0 + t),
                (x0 + w - t, y0 + t),
                (x0 + w - t, y0 + d - t),
                (x0 + t, y0 + d - t),
                (x0 + t, y0 + t),
            ]
            poly_inner = draw_polyline(target, pts_inner, close=True, layer=self.layer)
            if poly_inner:
                out.append(poly_inner)

        # 3. Seismic 135° Hooks (Double-line pairs extending inward into core)
        hk_len = self.effective_hook_length
        cos45 = math.cos(math.radians(45.0))
        sin45 = math.sin(math.radians(45.0))
        dx = hk_len * cos45
        dy = hk_len * sin45

        if self.hook_corner == "top_left":
            # Hook 1 (from top face turning down-right 135° into core):
            # Outer line & inner parallel line
            p1_out_start = (x0 + t * 2.5, y0 + d)
            p1_out_end = (p1_out_start[0] + dx, p1_out_start[1] - dy)
            l1_out = draw_line(target, p1_out_start, p1_out_end, layer=self.layer)
            if l1_out:
                out.append(l1_out)

            if self.double_line:
                p1_in_start = (x0 + t * 2.5, y0 + d - t)
                p1_in_end = (p1_in_start[0] + dx, p1_in_start[1] - dy)
                l1_in = draw_line(target, p1_in_start, p1_in_end, layer=self.layer)
                if l1_in:
                    out.append(l1_in)

            # Hook 2 (from left face turning down-right 135° into core):
            p2_out_start = (x0, y0 + d - t * 2.5)
            p2_out_end = (p2_out_start[0] + dx, p2_out_start[1] - dy)
            l2_out = draw_line(target, p2_out_start, p2_out_end, layer=self.layer)
            if l2_out:
                out.append(l2_out)

            if self.double_line:
                p2_in_start = (x0 + t, y0 + d - t * 2.5)
                p2_in_end = (p2_in_start[0] + dx, p2_in_start[1] - dy)
                l2_in = draw_line(target, p2_in_start, p2_in_end, layer=self.layer)
                if l2_in:
                    out.append(l2_in)

        elif self.hook_corner == "top_right":
            p1_out_start = (x0 + w - t * 2.5, y0 + d)
            p1_out_end = (p1_out_start[0] - dx, p1_out_start[1] - dy)
            l1_out = draw_line(target, p1_out_start, p1_out_end, layer=self.layer)
            if l1_out:
                out.append(l1_out)

            p2_out_start = (x0 + w, y0 + d - t * 2.5)
            p2_out_end = (p2_out_start[0] - dx, p2_out_start[1] - dy)
            l2_out = draw_line(target, p2_out_start, p2_out_end, layer=self.layer)
            if l2_out:
                out.append(l2_out)

        return out


def draw_double_line_stirrup(
    target: Any,
    *,
    width: float,
    depth: float,
    origin: tuple[float, float] = (0.0, 0.0),
    tie_diameter: float = 0.375,
    hook_length: float | None = None,
    hook_corner: str = "top_left",
    layer: str = "STIRRUP",
) -> list[Any]:
    """Helper function to draw a double-line stirrup with 135° seismic hooks."""
    st = StirrupGeometry(
        diameter=tie_diameter,
        width=width,
        depth=depth,
        origin=origin,
        hook_length=hook_length,
        hook_corner=hook_corner,
        double_line=True,
        layer=layer,
    )
    return st.draw(target)
