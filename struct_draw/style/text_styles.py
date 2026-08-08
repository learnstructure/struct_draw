"""TextStyle dataclass and registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator


@dataclass(frozen=True)
class TextStyle:
    """A DXF text-style definition.

    Attributes
    ----------
    name
        Unique text-style name.
    font
        Font file name or DXF font name (``"txt"``, ``"isocp"``,
        ``"complex"``, ``"romans"``, etc.).
    height
        Default text height in drawing units. ``0`` means
        "use the height specified at the TEXT / MTEXT entity".
    width_factor
        Width factor. ``1.0`` is normal width.
    oblique_angle
        Oblique angle in degrees. ``0`` is upright.
    """

    name: str
    font: str = "txt"
    height: float = 0.0
    width_factor: float = 1.0
    oblique_angle: float = 0.0


@dataclass
class TextStyleRegistry:
    text_styles: dict[str, TextStyle] = field(default_factory=dict)

    def add(self, text_style: TextStyle) -> None:
        if not text_style.name:
            raise ValueError("TextStyle name must be non-empty.")
        self.text_styles[text_style.name] = text_style

    def get(self, name: str) -> TextStyle | None:
        return self.text_styles.get(name)

    def require(self, name: str) -> TextStyle:
        try:
            return self.text_styles[name]
        except KeyError as exc:
            raise KeyError(
                f"TextStyle {name!r} is not registered. Add it via "
                f"``registry.add(TextStyle(name=...))`` before rendering."
            ) from exc

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self.text_styles

    def __iter__(self) -> Iterator[str]:
        return iter(self.text_styles)

    def __len__(self) -> int:
        return len(self.text_styles)


def default_registry() -> TextStyleRegistry:
    """Return the package-default text-style registry."""
    reg = TextStyleRegistry()
    reg.add(TextStyle("Standard", font="txt",       height=0.0, width_factor=1.0))
    reg.add(TextStyle("Title",    font="isocp",     height=0.25, width_factor=1.0))
    reg.add(TextStyle("Subtitle", font="isocp",     height=0.18, width_factor=1.0))
    reg.add(TextStyle("Dimension", font="isocp",    height=0.10, width_factor=1.0))
    reg.add(TextStyle("Note",      font="romans",   height=0.10, width_factor=0.9))
    reg.add(TextStyle("Schedule",  font="romans",   height=0.10, width_factor=1.0))
    reg.add(TextStyle("BarMark",   font="isocp",    height=0.10, width_factor=1.0))
    return reg


__all__ = ["TextStyle", "TextStyleRegistry", "default_registry"]