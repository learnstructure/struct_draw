"""Block dataclass and registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator, Mapping, Sequence


@dataclass(frozen=True)
class Block:
    """A reusable DXF block description.

    Attributes
    ----------
    name
        Unique block name.
    base_point
        ``(x, y)`` local origin for block insertion.
    description
        Optional human-readable description.
    primitives
        Sequence of primitive instructions. Each is a mapping with
        a ``"kind"`` key (``"line"``, ``"circle"``, ``"arc"``,
        ``"polyline"``, ``"text"``) plus the geometry payload.
    attributes
        Optional insertion-time attribute definitions (DXF
        ``ATTRIB`` entities).
    """

    name: str
    base_point: tuple[float, float] = (0.0, 0.0)
    description: str = ""
    primitives: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    attributes: Sequence[Mapping[str, Any]] = field(default_factory=tuple)


@dataclass
class BlockRegistry:
    blocks: dict[str, Block] = field(default_factory=dict)

    def add(self, block: Block) -> None:
        if not block.name:
            raise ValueError("Block name must be non-empty.")
        self.blocks[block.name] = block

    def get(self, name: str) -> Block | None:
        return self.blocks.get(name)

    def require(self, name: str) -> Block:
        try:
            return self.blocks[name]
        except KeyError as exc:
            raise KeyError(
                f"Block {name!r} is not registered. Add it via "
                f"``registry.add(Block(name=...))`` before rendering."
            ) from exc

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self.blocks

    def __iter__(self) -> Iterator[str]:
        return iter(self.blocks)

    def __len__(self) -> int:
        return len(self.blocks)


def default_registry() -> BlockRegistry:
    """Return the package-default block registry."""
    reg = BlockRegistry()

    reg.add(
        Block(
            name="SECTION_CUT",
            base_point=(0.0, 0.0),
            description="Section-cut symbol (ACI)",
            primitives=(
                {"kind": "circle", "center": (0.0, 0.0), "radius": 0.5},
                {"kind": "text",   "position": (0.0, 0.0), "text": "A",
                 "height": 0.35, "align": "center"},
            ),
            attributes=(
                {"tag": "LETTER", "prompt": "Section letter",
                 "default": "A", "position": (0.0, 0.0)},
            ),
        )
    )

    reg.add(
        Block(
            name="REBAR_MARK",
            base_point=(0.0, 0.0),
            description="Rebar mark label",
            primitives=(
                {"kind": "circle", "center": (0.0, 0.0), "radius": 0.18},
            ),
            attributes=(
                {"tag": "MARK",   "prompt": "Bar mark",
                 "default": "1", "position": (0.0, 0.0)},
                {"tag": "QTY",    "prompt": "Quantity",
                 "default": "1", "position": (0.0, -0.35)},
            ),
        )
    )

    reg.add(
        Block(
            name="NORTH_ARROW",
            base_point=(0.0, 0.0),
            description="North arrow",
            primitives=(
                {"kind": "polyline",
                 "points": [(0.0, 0.5), (-0.2, -0.3), (0.0, 0.0), (0.2, -0.3), (0.0, 0.5)]},
                {"kind": "text", "position": (0.0, -0.55), "text": "N",
                 "height": 0.20, "align": "center"},
            ),
        )
    )

    reg.add(
        Block(
            name="BEAM_SECTION",
            base_point=(0.0, 0.0),
            description="Beam cross-section block (outline + stirrup + 6 bar dots).",
            primitives=(
                {"kind": "polyline",
                 "points": [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5), (-0.5, -0.5)]},
                {"kind": "polyline",
                 "points": [(-0.375, -0.375), (0.375, -0.375), (0.375, 0.375), (-0.375, 0.375), (-0.375, -0.375)]},
                {"kind": "circle", "center": (-0.31, -0.31), "radius": 0.06},
                {"kind": "circle", "center": (0.0, -0.31), "radius": 0.06},
                {"kind": "circle", "center": (0.31, -0.31), "radius": 0.06},
                {"kind": "circle", "center": (-0.31, 0.31), "radius": 0.06},
                {"kind": "circle", "center": (0.0, 0.31), "radius": 0.06},
                {"kind": "circle", "center": (0.31, 0.31), "radius": 0.06},
            ),
        )
    )

    return reg


__all__ = ["Block", "BlockRegistry", "default_registry"]