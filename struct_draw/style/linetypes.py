"""LineType dataclass and registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Sequence


@dataclass(frozen=True)
class LineType:
    """A DXF line-type definition.

    Attributes
    ----------
    name
        Unique line-type name. Referenced from :class:`Layer.linetype`.
    pattern
        Dash / dot pattern as a sequence of signed lengths.
        Positive values are dashes, negative are gaps, ``0`` is a
        dot. Example: ``[0.25, -0.125, 0.0, -0.125]`` =
        dash 0.25, gap 0.125, dot, gap 0.125.
    description
        Optional human-readable description.
    """

    name: str
    pattern: Sequence[float]
    description: str = ""


@dataclass
class LineTypeRegistry:
    """A name → :class:`LineType` mapping with dict-like helpers."""

    linetypes: dict[str, LineType] = field(default_factory=dict)

    def add(self, linetype: LineType) -> None:
        if not linetype.name:
            raise ValueError("LineType name must be non-empty.")
        self.linetypes[linetype.name] = linetype

    def get(self, name: str) -> LineType | None:
        return self.linetypes.get(name)

    def require(self, name: str) -> LineType:
        try:
            return self.linetypes[name]
        except KeyError as exc:
            raise KeyError(
                f"LineType {name!r} is not registered. Add it via "
                f"``registry.add(LineType(name=...))`` before rendering."
            ) from exc

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self.linetypes

    def __iter__(self) -> Iterator[str]:
        return iter(self.linetypes)

    def __len__(self) -> int:
        return len(self.linetypes)


def default_registry() -> LineTypeRegistry:
    """Return the package-default line-type registry."""
    reg = LineTypeRegistry()
    reg.add(LineType("Continuous", [], description="Solid line"))
    reg.add(LineType("Dashed",     [0.5, -0.25], description="Standard dashed"))
    reg.add(LineType("Dashed2",    [0.25, -0.125], description="Short dashed"))
    reg.add(LineType("Hidden",     [0.125, -0.0625], description="Hidden / dashed short"))
    reg.add(LineType("Center",     [0.5, -0.125, 0.125, -0.125], description="Center line (dash-dot)"))
    reg.add(LineType("Phantom",    [0.5, -0.125, 0.125, -0.125, 0.125, -0.125], description="Phantom (dash-dot-dot)"))
    reg.add(LineType("Dot",        [0.0, -0.125], description="Dotted"))
    reg.add(LineType("DashDot",    [0.5, -0.125, 0.0, -0.125], description="Dash-dot"))
    return reg


__all__ = ["LineType", "LineTypeRegistry", "default_registry"]