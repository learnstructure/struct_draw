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
    corner_bar_diameter: float | None = None
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
        is_metric = self.width >= 100.0 or self.depth >= 100.0 or self.diameter >= 5.0

        # Corner longitudinal rebar radius determination
        if self.corner_bar_diameter is not None and self.corner_bar_diameter > 0:
            r_b = self.corner_bar_diameter / 2.0
        elif self.bend_radius is not None and self.bend_radius > 0:
            r_b = self.bend_radius
        else:
            r_b = max(0.8 * t, 8.0 if is_metric else 0.3125)
        # Ensure r_b fits within the cross-section
        r_b = min(r_b, 0.35 * w, 0.35 * d)

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

        # 2. Seismic 135° Hooks parameters
        hk_len = self.effective_hook_length
        cos45 = math.cos(math.radians(45.0))
        sin45 = math.sin(math.radians(45.0))
        dx = hk_len * cos45
        dy = hk_len * sin45
        clr = 0.02 * t
        sqrt2 = math.sqrt(2.0)

        corner = self.hook_corner.lower()

        if corner == "top_left":
            rcx = x0 + t + r_b
            rcy = y0 + d - t - r_b
            nx, ny = sin45, cos45

            # Hook 1 (top)
            X1 = rcx + (sqrt2 - 1.0) * r_b + clr
            Y1 = y0 + d - t
            h1_in_start = (X1, Y1)
            h1_in_end = (X1 + dx, Y1 - dy)
            h1_out_end = (h1_in_end[0] + t * nx, h1_in_end[1] + t * ny)
            h1_out_start = (X1 + t * sqrt2, Y1)

            # Hook 2 (left)
            X2 = x0 + t
            Y2 = rcy - (sqrt2 - 1.0) * r_b - clr
            h2_in_start = (X2, Y2)
            h2_in_end = (X2 + dx, Y2 - dy)
            h2_out_end = (h2_in_end[0] - t * nx, h2_in_end[1] - t * ny)
            h2_out_start = (X2, Y2 - t * sqrt2)

            arc_pts = []
            for i in range(1, 5):
                deg = -90.0 + i * (90.0 / 5.0)
                rad = math.radians(deg)
                arc_pts.append((rcx + (r_b + clr) * math.cos(rad), rcy + (r_b + clr) * math.sin(rad)))

            inner_poly = [
                h1_out_start,
                (x0 + w - t, y0 + d - t),
                (x0 + w - t, y0 + t),
                (x0 + t, y0 + t),
                h2_out_start,
                h2_out_end,
                h2_in_end,
                h2_in_start,
            ] + arc_pts + [
                h1_in_start,
                h1_in_end,
                h1_out_end,
                h1_out_start,
            ]
            single_poly = [h2_in_end, h2_in_start, (x0, y0), (x0 + w, y0), (x0 + w, y0 + d), h1_in_start, h1_in_end]

        elif corner == "top_right":
            rcx = x0 + w - t - r_b
            rcy = y0 + d - t - r_b
            nx, ny = -sin45, cos45

            # Hook 1 (top)
            X1 = rcx - (sqrt2 - 1.0) * r_b - clr
            Y1 = y0 + d - t
            h1_in_start = (X1, Y1)
            h1_in_end = (X1 - dx, Y1 - dy)
            h1_out_end = (h1_in_end[0] + t * nx, h1_in_end[1] + t * ny)
            h1_out_start = (X1 - t * sqrt2, Y1)

            # Hook 2 (right)
            X2 = x0 + w - t
            Y2 = rcy - (sqrt2 - 1.0) * r_b - clr
            h2_in_start = (X2, Y2)
            h2_in_end = (X2 - dx, Y2 - dy)
            h2_out_end = (h2_in_end[0] - t * nx, h2_in_end[1] - t * ny)
            h2_out_start = (X2, Y2 - t * sqrt2)

            arc_pts = []
            for i in range(1, 5):
                deg = -90.0 - i * (90.0 / 5.0)
                rad = math.radians(deg)
                arc_pts.append((rcx + (r_b + clr) * math.cos(rad), rcy + (r_b + clr) * math.sin(rad)))

            inner_poly = [
                h2_out_start,
                (x0 + w - t, y0 + t),
                (x0 + t, y0 + t),
                (x0 + t, y0 + d - t),
                h1_out_start,
                h1_out_end,
                h1_in_end,
                h1_in_start,
            ] + arc_pts + [
                h2_in_start,
                h2_in_end,
                h2_out_end,
                h2_out_start,
            ]
            single_poly = [h1_in_end, h1_in_start, (x0, y0 + d), (x0, y0), (x0 + w, y0), h2_in_start, h2_in_end]

        elif corner == "bottom_left":
            rcx = x0 + t + r_b
            rcy = y0 + t + r_b
            nx, ny = sin45, -cos45

            # Hook 1 (bottom)
            X1 = rcx + (sqrt2 - 1.0) * r_b + clr
            Y1 = y0 + t
            h1_in_start = (X1, Y1)
            h1_in_end = (X1 + dx, Y1 + dy)
            h1_out_end = (h1_in_end[0] + t * nx, h1_in_end[1] + t * ny)
            h1_out_start = (X1 + t * sqrt2, Y1)

            # Hook 2 (left)
            X2 = x0 + t
            Y2 = rcy + (sqrt2 - 1.0) * r_b + clr
            h2_in_start = (X2, Y2)
            h2_in_end = (X2 + dx, Y2 + dy)
            h2_out_end = (h2_in_end[0] - t * nx, h2_in_end[1] - t * ny)
            h2_out_start = (X2, Y2 + t * sqrt2)

            arc_pts = []
            for i in range(1, 5):
                deg = 90.0 - i * (90.0 / 5.0)
                rad = math.radians(deg)
                arc_pts.append((rcx + (r_b + clr) * math.cos(rad), rcy + (r_b + clr) * math.sin(rad)))

            inner_poly = [
                h2_out_start,
                (x0 + t, y0 + d - t),
                (x0 + w - t, y0 + d - t),
                (x0 + w - t, y0 + t),
                h1_out_start,
                h1_out_end,
                h1_in_end,
                h1_in_start,
            ] + arc_pts + [
                h2_in_start,
                h2_in_end,
                h2_out_end,
                h2_out_start,
            ]
            single_poly = [h1_in_end, h1_in_start, (x0 + w, y0), (x0 + w, y0 + d), (x0, y0 + d), h2_in_start, h2_in_end]

        else:  # bottom_right
            rcx = x0 + w - t - r_b
            rcy = y0 + t + r_b
            nx, ny = -sin45, -cos45

            # Hook 1 (bottom)
            X1 = rcx - (sqrt2 - 1.0) * r_b - clr
            Y1 = y0 + t
            h1_in_start = (X1, Y1)
            h1_in_end = (X1 - dx, Y1 + dy)
            h1_out_end = (h1_in_end[0] + t * nx, h1_in_end[1] + t * ny)
            h1_out_start = (X1 - t * sqrt2, Y1)

            # Hook 2 (right)
            X2 = x0 + w - t
            Y2 = rcy + (sqrt2 - 1.0) * r_b + clr
            h2_in_start = (X2, Y2)
            h2_in_end = (X2 - dx, Y2 + dy)
            h2_out_end = (h2_in_end[0] - t * nx, h2_in_end[1] - t * ny)
            h2_out_start = (X2, Y2 + t * sqrt2)

            arc_pts = []
            for i in range(1, 5):
                deg = 90.0 + i * (90.0 / 5.0)
                rad = math.radians(deg)
                arc_pts.append((rcx + (r_b + clr) * math.cos(rad), rcy + (r_b + clr) * math.sin(rad)))

            inner_poly = [
                h1_out_start,
                (x0 + t, y0 + t),
                (x0 + t, y0 + d - t),
                (x0 + w - t, y0 + d - t),
                h2_out_start,
                h2_out_end,
                h2_in_end,
                h2_in_start,
            ] + arc_pts + [
                h1_in_start,
                h1_in_end,
                h1_out_end,
                h1_out_start,
            ]
            single_poly = [h2_in_end, h2_in_start, (x0 + w, y0 + d), (x0, y0 + d), (x0, y0), h1_in_start, h1_in_end]

        if self.double_line and w > 2.0 * t and d > 2.0 * t:
            p_in = draw_polyline(target, inner_poly, close=True, layer=self.layer)
            if p_in:
                out.append(p_in)
        else:
            p_s = draw_polyline(target, single_poly, close=False, layer=self.layer)
            if p_s:
                out.append(p_s)

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
    corner_bar_diameter: float | None = None,
    bend_radius: float | None = None,
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
        corner_bar_diameter=corner_bar_diameter,
        bend_radius=bend_radius,
        double_line=True,
        layer=layer,
    )
    return st.draw(target)
