"""Layer dataclass and registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator


@dataclass(frozen=True)
class Layer:
    """A DXF layer definition.

    Attributes
    ----------
    name
        Unique layer name.
    color
        DXF color index (1-255). ``None`` lets the backend pick.
        Common ACI 318 conventions:
        * ``1``  — red    (rebar in section / plan)
        * ``7``  — white  (concrete outline)
        * ``252`` — light gray (hidden lines)
        * ``3``  — green  (dimensions)
        * ``5``  — blue   (annotations / general notes)
    linetype
        Name of a :class:`struct_draw.style.LineType`. Common
        values: ``"Continuous"``, ``"Dashed"``, ``"Hidden"``,
        ``"Center"``.
    lineweight
        DXF lineweight in 1/100 mm. ``-1`` means "default".
    on
        Whether the layer is enabled.
    plot
        Whether the layer is plotted.
    description
        Optional human-readable description.
    """

    name: str
    color: int | None = 7
    linetype: str = "Continuous"
    lineweight: int = -1
    on: bool = True
    plot: bool = True
    description: str = ""


@dataclass
class LayerRegistry:
    """A name → :class:`Layer` mapping with dict-like helpers."""

    layers: dict[str, Layer] = field(default_factory=dict)

    def add(self, layer: Layer) -> None:
        if not layer.name:
            raise ValueError("Layer name must be non-empty.")
        self.layers[layer.name] = layer

    def get(self, name: str) -> Layer | None:
        return self.layers.get(name)

    def require(self, name: str) -> Layer:
        try:
            return self.layers[name]
        except KeyError as exc:
            raise KeyError(
                f"Layer {name!r} is not registered. Add it via "
                f"``registry.add(Layer(name=...))`` before rendering."
            ) from exc

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self.layers

    def __iter__(self) -> Iterator[str]:
        return iter(self.layers)

    def __len__(self) -> int:
        return len(self.layers)


def default_registry() -> LayerRegistry:
    """Return the package-default layer registry.

    Follows typical ACI 318 / US structural-drawing conventions.
    """
    reg = LayerRegistry()
    reg.add(Layer("0",         color=7, linetype="Continuous", description="DXF default layer"))
    reg.add(Layer("CONC_OUTLINE", color=7, linetype="Continuous", description="Concrete outlines (visible)"))
    reg.add(Layer("CONC_HIDDEN",  color=252, linetype="Hidden",  description="Concrete outlines (hidden)"))
    reg.add(Layer("REBAR",        color=1,   linetype="Continuous", description="Reinforcement (visible)"))
    reg.add(Layer("REBAR_HIDDEN", color=1,   linetype="Hidden",    description="Reinforcement (hidden)"))
    reg.add(Layer("STIRRUP",      color=1,   linetype="Dashed",    description="Stirrups / ties"))
    reg.add(Layer("HOOK",         color=1,   linetype="Continuous", description="Hooks and bends"))
    reg.add(Layer("SPLICE",       color=2,   linetype="Phantom",   description="Lap splices"))
    reg.add(Layer("DIM_LINEAR",   color=3,   linetype="Continuous", description="Linear dimensions"))
    reg.add(Layer("DIM_ANGULAR",  color=3,   linetype="Continuous", description="Angular dimensions"))
    reg.add(Layer("DIM_RADIAL",   color=3,   linetype="Continuous", description="Radial dimensions"))
    reg.add(Layer("LEADER",       color=3,   linetype="Continuous", description="Leader lines / annotations"))
    reg.add(Layer("TEXT",         color=5,   linetype="Continuous", description="General text / notes"))
    reg.add(Layer("TITLE",        color=5,   linetype="Continuous", description="Title block / sheet headers"))
    reg.add(Layer("SCHEDULE",     color=5,   linetype="Continuous", description="Bar schedules"))
    reg.add(Layer("HATCH",        color=8,   linetype="Continuous", description="Concrete / material hatches"))
    reg.add(Layer("CENTERLINE",   color=4,   linetype="Center",     description="Center lines"))
    reg.add(Layer("SECTION_CUT",  color=6,   linetype="Continuous", description="Section cuts / view labels"))
    reg.add(Layer("GRID",         color=4,   linetype="Continuous", description="Plan grid lines"))
    reg.add(Layer("BREAK_LINE",   color=7,   linetype="Continuous", description="Break lines (continues above)"))
    reg.add(Layer("LEVEL",        color=4,   linetype="Continuous", description="Ground / plinth level lines"))
    reg.add(Layer("BAR_MARK",     color=5,   linetype="Continuous", description="Bar mark labels"))
    reg.add(Layer("FOUNDATION",   color=105, linetype="Continuous", description="Foundation outline"))
    reg.add(Layer("COLUMN",       color=5,   linetype="Continuous", description="Column outline"))
    reg.add(Layer("BEAM",         color=10,  linetype="Continuous", description="Beam outline"))
    reg.add(Layer("Foundation",   color=105, linetype="Continuous", description="Foundation outline"))
    reg.add(Layer("Column",       color=5,   linetype="Continuous", description="Column outline"))
    reg.add(Layer("Beam",         color=10,  linetype="Continuous", description="Beam outline"))
    reg.add(Layer("Rebar",        color=2,   linetype="Continuous", description="Rebar outline"))
    reg.add(Layer("Rebar_hatch",  color=2,   linetype="Continuous", lineweight=50, description="Rebar section hatch"))
    reg.add(Layer("Dimension",    color=132, linetype="Continuous", description="Dimension lines"))
    reg.add(Layer("Stirrup",      color=135, linetype="Continuous", description="Stirrups"))
    reg.add(Layer("Text",         color=151, linetype="Continuous", description="Text and annotations"))
    reg.add(Layer("Level",        color=8,   linetype="Continuous", description="Level lines"))
    reg.add(Layer("CEN",          color=132, linetype="Center",     description="Centerlines"))
    return reg


__all__ = ["Layer", "LayerRegistry", "default_registry"]