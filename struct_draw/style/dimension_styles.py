"""DimensionStyle dataclass and registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator


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


def default_registry(is_metric: bool = True) -> DimensionStyleRegistry:
    """Return the package-default dimension-style registry."""
    reg = DimensionStyleRegistry()
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
    return reg


__all__ = [
    "ArrowheadKind",
    "DimensionStyle",
    "DimensionStyleRegistry",
    "default_registry",
]