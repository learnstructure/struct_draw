"""DimensionStyle dataclass and registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterator, Optional


class ArrowheadKind(str, Enum):
    """Arrowhead / tick-mark styles."""

    FILLED_TRIANGLE = "filled_triangle"
    OPEN_ARROW = "open_arrow"
    SLASH = "slash"
    DOT = "dot"
    ARCBALL = "arcball"
    NONE = "none"


@dataclass(frozen=True)
class DimensionStyle:
    """A DXF dimension-style definition.

    Attributes
    ----------
    name
        Unique dimension-style name.
    text_style
        Name of a :class:`struct_draw.style.TextStyle` used for
        the dimension text.
    arrow_kind
        Arrowhead / tick-mark kind. See :class:`ArrowheadKind`.
    arrow_size
        Arrowhead size in drawing units.
    extension_offset
        Distance from the entity to the start of the extension line.
    extension_extension
        Distance the extension line extends past the dimension line.
    fixed_extension_len
        Fixed length for extension lines. If None, defaults to extension_extension.
    text_height
        Override for the text height.
    """

    name: str
    text_style: str = "Dimension"
    arrow_kind: ArrowheadKind = ArrowheadKind.FILLED_TRIANGLE
    arrow_size: float = 50.0
    extension_offset: float = 50.0
    extension_extension: float = 50.0
    fixed_extension_len: float | None = None
    text_height: float | None = 100.0


@dataclass
class DimensionStyleRegistry:
    styles: dict[str, DimensionStyle] = field(default_factory=dict)

    def add(self, style: DimensionStyle) -> None:
        if not style.name:
            raise ValueError("DimensionStyle name must be non-empty.")
        self.styles[style.name] = style

    def get(self, name: str) -> DimensionStyle | None:
        return self.styles.get(name)

    def require(self, name: str) -> DimensionStyle:
        try:
            return self.styles[name]
        except KeyError as exc:
            raise KeyError(
                f"DimensionStyle {name!r} is not registered. Add it via "
                f"``registry.add(DimensionStyle(name=...))`` before rendering."
            ) from exc

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self.styles

    def __iter__(self) -> Iterator[str]:
        return iter(self.styles)

    def __len__(self) -> int:
        return len(self.styles)


def default_registry(
    is_metric: bool = True,
    scale: Optional[Any] = None,
    unit: Optional[Any] = None,
) -> DimensionStyleRegistry:
    """Return the package-default dimension-style registry.

    Parameters
    ----------
    is_metric : bool
        True for Metric (mm), False for Imperial (in).
    scale : DrawingScale, optional
        Optional specific view scale. If omitted, standard defaults (1:50 / 1/4\"=1'-0\")
        are used.
    unit : DrawingUnit, optional
        Drawing unit (DrawingUnit.MM, DrawingUnit.IN, etc.).
    """
    from struct_draw.core.units import DrawingScale, DrawingUnit
    from struct_draw.style.annotation_config import DEFAULT_ANNOTATION_CONFIG

    d_unit = unit or (DrawingUnit.MM if is_metric else DrawingUnit.IN)
    reg = DimensionStyleRegistry()

    if scale is not None:
        th = DEFAULT_ANNOTATION_CONFIG.dim_text_height(scale, d_unit)
        asz = DEFAULT_ANNOTATION_CONFIG.arrow_size(scale, d_unit)
        ext = DEFAULT_ANNOTATION_CONFIG.dim_extension(scale, d_unit)
        fxl = ext
    else:
        # Default baseline ensuring backward compatibility
        th = 100.0 if is_metric else 4.0
        asz = 50.0 if is_metric else 2.0
        ext = 50.0 if is_metric else 2.0
        fxl = 50.0 if is_metric else 2.0

    reg.add(DimensionStyle("Linear",    text_style="Dimension", arrow_kind=ArrowheadKind.FILLED_TRIANGLE, text_height=th, arrow_size=asz, extension_offset=ext, extension_extension=ext, fixed_extension_len=fxl))
    reg.add(DimensionStyle("Metric",    text_style="Dimension", arrow_kind=ArrowheadKind.FILLED_TRIANGLE, text_height=th, arrow_size=asz, extension_offset=ext, extension_extension=ext, fixed_extension_len=fxl))
    reg.add(DimensionStyle("Dimension", text_style="Dimension", arrow_kind=ArrowheadKind.FILLED_TRIANGLE, text_height=th, arrow_size=asz, extension_offset=ext, extension_extension=ext, fixed_extension_len=fxl))
    reg.add(DimensionStyle("Angular",   text_style="Dimension", arrow_kind=ArrowheadKind.FILLED_TRIANGLE, text_height=th, arrow_size=asz, extension_offset=ext, extension_extension=ext, fixed_extension_len=fxl))
    reg.add(DimensionStyle("Radial",    text_style="Dimension", arrow_kind=ArrowheadKind.OPEN_ARROW, text_height=th, arrow_size=asz, extension_offset=ext, extension_extension=ext, fixed_extension_len=fxl))
    reg.add(DimensionStyle("Leader",    text_style="Note",      arrow_kind=ArrowheadKind.NONE, text_height=th, arrow_size=asz, extension_offset=ext, extension_extension=ext, fixed_extension_len=fxl))
    reg.add(DimensionStyle("Slope",     text_style="Dimension", arrow_kind=ArrowheadKind.SLASH, text_height=th, arrow_size=asz, extension_offset=ext, extension_extension=ext, fixed_extension_len=fxl))

    # Add standard scale-specific dimension styles for multi-scale sheets
    if is_metric:
        scales_metric = [
            ("DIM_1_100", DrawingScale.metric(100.0)),
            ("DIM_PLAN", DrawingScale.metric(100.0)),
            ("DIM_1_50", DrawingScale.metric(50.0)),
            ("DIM_ELEV", DrawingScale.metric(50.0)),
            ("DIM_1_25", DrawingScale.metric(25.0)),
            ("DIM_1_20", DrawingScale.metric(20.0)),
            ("DIM_DETAIL", DrawingScale.metric(20.0)),
            ("DIM_1_10", DrawingScale.metric(10.0)),
        ]
        for s_name, sc in scales_metric:
            s_th = DEFAULT_ANNOTATION_CONFIG.dim_text_height(sc, DrawingUnit.MM)
            s_asz = DEFAULT_ANNOTATION_CONFIG.arrow_size(sc, DrawingUnit.MM)
            s_ext = DEFAULT_ANNOTATION_CONFIG.dim_extension(sc, DrawingUnit.MM)
            reg.add(DimensionStyle(
                s_name,
                text_style="Dimension",
                arrow_kind=ArrowheadKind.FILLED_TRIANGLE,
                text_height=s_th,
                arrow_size=s_asz,
                extension_offset=s_ext,
                extension_extension=s_ext,
                fixed_extension_len=s_ext,
            ))
    else:
        scales_imperial = [
            ("DIM_1_8_IN", DrawingScale.imperial('1/8" = 1\'-0"')),
            ("DIM_PLAN", DrawingScale.imperial('1/8" = 1\'-0"')),
            ("DIM_1_4_IN", DrawingScale.imperial('1/4" = 1\'-0"')),
            ("DIM_ELEV", DrawingScale.imperial('1/4" = 1\'-0"')),
            ("DIM_1_2_IN", DrawingScale.imperial('1/2" = 1\'-0"')),
            ("DIM_3_4_IN", DrawingScale.imperial('3/4" = 1\'-0"')),
            ("DIM_1_IN", DrawingScale.imperial('1" = 1\'-0"')),
            ("DIM_DETAIL", DrawingScale.imperial('1" = 1\'-0"')),
            ("DIM_3_IN", DrawingScale.imperial('3" = 1\'-0"')),
        ]
        for s_name, sc in scales_imperial:
            s_th = DEFAULT_ANNOTATION_CONFIG.dim_text_height(sc, DrawingUnit.IN)
            s_asz = DEFAULT_ANNOTATION_CONFIG.arrow_size(sc, DrawingUnit.IN)
            s_ext = DEFAULT_ANNOTATION_CONFIG.dim_extension(sc, DrawingUnit.IN)
            reg.add(DimensionStyle(
                s_name,
                text_style="Dimension",
                arrow_kind=ArrowheadKind.FILLED_TRIANGLE,
                text_height=s_th,
                arrow_size=s_asz,
                extension_offset=s_ext,
                extension_extension=s_ext,
                fixed_extension_len=s_ext,
            ))

    return reg


__all__ = [
    "ArrowheadKind",
    "DimensionStyle",
    "DimensionStyleRegistry",
    "default_registry",
]