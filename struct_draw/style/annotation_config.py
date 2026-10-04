"""struct_draw.style.annotation_config — Standard drafting print sizes & scale calculators.

Implements the universal drafting rule:
- Dimensions: ~2.0 mm on paper
- Text / Notes: ~3.0 mm on paper
- Titles: ~5.0 mm on paper
- Arrowheads: ~2.0 mm on paper
- Dimension offset: ~6.0 mm on paper
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Union

from struct_draw.core.units import DrawingScale, DrawingUnit, SCALE_1_50, SCALE_1_4_IN
from struct_draw.style.dimension_styles import ArrowheadKind, DimensionStyle


@dataclass(frozen=True)
class AnnotationConfig:
    """Configures target paper-space print dimensions (in millimeters).

    Attributes
    ----------
    dim_text_mm : float
        Target plotted dimension text height on paper (default 2.0 mm).
    text_mm : float
        Target plotted general text / notes / labels height on paper (default 3.0 mm).
    title_mm : float
        Target plotted view title height on paper (default 5.0 mm).
    subtitle_mm : float
        Target plotted view subtitle / scale text height on paper (default 3.5 mm).
    arrow_mm : float
        Target plotted arrowhead / tick size on paper (default 2.0 mm).
    dim_offset_mm : float
        Target plotted dimension line clearance offset from object (default 6.0 mm).
    dim_extension_mm : float
        Target plotted extension line overhang past dimension line (default 2.0 mm).
    bubble_radius_mm : float
        Target plotted grid bubble radius on paper (default 4.0 mm).
    """

    dim_text_mm: float = 2.0
    text_mm: float = 3.0
    title_mm: float = 5.0
    subtitle_mm: float = 3.5
    arrow_mm: float = 2.0
    dim_offset_mm: float = 6.0
    dim_extension_mm: float = 2.0
    bubble_radius_mm: float = 4.0

    def _convert_mm_to_unit(self, mm_val: float, unit: DrawingUnit) -> float:
        """Convert a paper millimeter measurement into modelspace drawing units."""
        return mm_val / unit.scale_to_mm

    def _resolve_unit(self, unit: Any) -> DrawingUnit:
        """Resolve unit input into a DrawingUnit enum."""
        if isinstance(unit, DrawingUnit):
            return unit
        if isinstance(unit, str):
            try:
                return DrawingUnit.from_str(unit)
            except Exception:
                pass
        return DrawingUnit.MM

    def _resolve_scale(self, scale: Any, unit: DrawingUnit) -> DrawingScale:
        """Resolve scale input (DrawingScale, float, int, str, None) into a DrawingScale."""
        if isinstance(scale, DrawingScale):
            return scale
        if isinstance(scale, (int, float)):
            f_val = float(scale)
            if f_val <= 0:
                return SCALE_1_50 if unit.is_metric else SCALE_1_4_IN
            r = (1.0 / f_val) if f_val < 1.0 else f_val
            name = f"1:{int(r)}" if r.is_integer() else f"1:{r:.1f}"
            return DrawingScale(ratio=r, name=name, is_metric=unit.is_metric)
        if isinstance(scale, str):
            try:
                return DrawingScale.from_str(scale, is_metric=unit.is_metric)
            except Exception:
                pass
        return SCALE_1_50 if unit.is_metric else SCALE_1_4_IN

    def dim_text_height(
        self,
        scale: Any = None,
        unit: Any = None,
    ) -> float:
        """Calculate modelspace dimension text height for given scale and unit."""
        u = self._resolve_unit(unit)
        s = self._resolve_scale(scale, u)
        return self._convert_mm_to_unit(self.dim_text_mm, u) * s.ratio

    def text_height(
        self,
        scale: Any = None,
        unit: Any = None,
    ) -> float:
        """Calculate modelspace general text height (3.0 mm plotted) for given scale and unit."""
        u = self._resolve_unit(unit)
        s = self._resolve_scale(scale, u)
        return self._convert_mm_to_unit(self.text_mm, u) * s.ratio

    def title_height(
        self,
        scale: Any = None,
        unit: Any = None,
    ) -> float:
        """Calculate modelspace view title height (5.0 mm plotted) for given scale and unit."""
        u = self._resolve_unit(unit)
        s = self._resolve_scale(scale, u)
        return self._convert_mm_to_unit(self.title_mm, u) * s.ratio

    def subtitle_height(
        self,
        scale: Any = None,
        unit: Any = None,
    ) -> float:
        """Calculate modelspace subtitle height (3.5 mm plotted) for given scale and unit."""
        u = self._resolve_unit(unit)
        s = self._resolve_scale(scale, u)
        return self._convert_mm_to_unit(self.subtitle_mm, u) * s.ratio

    def arrow_size(
        self,
        scale: Any = None,
        unit: Any = None,
    ) -> float:
        """Calculate modelspace arrowhead size (2.0 mm plotted) for given scale and unit."""
        u = self._resolve_unit(unit)
        s = self._resolve_scale(scale, u)
        return self._convert_mm_to_unit(self.arrow_mm, u) * s.ratio

    def dim_offset(
        self,
        scale: Any = None,
        unit: Any = None,
    ) -> float:
        """Calculate modelspace dimension clearance offset (6.0 mm plotted)."""
        u = self._resolve_unit(unit)
        s = self._resolve_scale(scale, u)
        return self._convert_mm_to_unit(self.dim_offset_mm, u) * s.ratio

    def dim_extension(
        self,
        scale: Any = None,
        unit: Any = None,
    ) -> float:
        """Calculate modelspace extension line overhang (2.0 mm plotted)."""
        u = self._resolve_unit(unit)
        s = self._resolve_scale(scale, u)
        return self._convert_mm_to_unit(self.dim_extension_mm, u) * s.ratio

    def bubble_radius(
        self,
        scale: Any = None,
        unit: Any = None,
    ) -> float:
        """Calculate modelspace grid bubble radius (4.0 mm plotted)."""
        u = self._resolve_unit(unit)
        s = self._resolve_scale(scale, u)
        return self._convert_mm_to_unit(self.bubble_radius_mm, u) * s.ratio

    def create_dimension_style(
        self,
        name: str,
        scale: Any = None,
        unit: Any = None,
        *,
        arrow_kind: ArrowheadKind = ArrowheadKind.FILLED_TRIANGLE,
        text_style: str = "Dimension",
    ) -> DimensionStyle:
        """Create a DimensionStyle accurately scaled for the given viewport scale and unit."""
        th = self.dim_text_height(scale, unit)
        asz = self.arrow_size(scale, unit)
        ext = self.dim_extension(scale, unit)
        off = self.dim_offset(scale, unit)
        return DimensionStyle(
            name=name,
            text_style=text_style,
            arrow_kind=arrow_kind,
            text_height=th,
            arrow_size=asz,
            extension_offset=off * 0.5,
            extension_extension=ext,
            fixed_extension_len=ext,
        )


# Global default annotation configuration instance
DEFAULT_ANNOTATION_CONFIG = AnnotationConfig()
