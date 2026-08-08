"""Unit tests for the v2 style registries. Pure data-layer tests."""

from __future__ import annotations

import pytest

from struct_draw.style.layers import Layer, LayerRegistry, default_registry as default_layers
from struct_draw.style.linetypes import LineType, LineTypeRegistry
from struct_draw.style.text_styles import TextStyle, TextStyleRegistry
from struct_draw.style.dimension_styles import (
    DimensionStyle,
    DimensionStyleRegistry,
)
from struct_draw.style.blocks import (
    Block,
    BlockRegistry,
    default_registry as default_blocks,
)


def test_layer_registry_add_and_lookup() -> None:
    reg = LayerRegistry()
    reg.add(Layer(name="REBAR", color=1))
    assert "REBAR" in reg
    assert reg.require("REBAR").color == 1
    with pytest.raises(KeyError):
        reg.require("NOPE")


def test_layer_registry_empty_name_raises() -> None:
    reg = LayerRegistry()
    with pytest.raises(ValueError):
        reg.add(Layer(name=""))


def test_default_layer_registry_has_known_names() -> None:
    reg = default_layers()
    for required in ("REBAR", "CONC_OUTLINE", "DIM_LINEAR"):
        assert required in reg


def test_linetype_registry_patterns() -> None:
    reg = LineTypeRegistry()
    reg.add(LineType(name="Dashed", pattern=[0.5, -0.25]))
    assert reg.require("Dashed").pattern == [0.5, -0.25]


def test_text_style_defaults() -> None:
    reg = TextStyleRegistry()
    reg.add(TextStyle(name="Title", height=0.25, font="isocp"))
    ts = reg.require("Title")
    assert ts.height == 0.25 and ts.font == "isocp"


def test_dimension_style_registry() -> None:
    reg = DimensionStyleRegistry()
    reg.add(
        DimensionStyle(
            name="Linear",
            text_style="Dimension",
            arrow_size=0.10,
        )
    )
    ds = reg.require("Linear")
    assert ds.arrow_size == pytest.approx(0.10)


def test_block_registry_has_section_cut() -> None:
    reg = default_blocks()
    assert "SECTION_CUT" in reg
    assert "REBAR_MARK" in reg
    assert "NORTH_ARROW" in reg


def test_block_registry_empty_name_raises() -> None:
    reg = BlockRegistry()
    with pytest.raises(ValueError):
        reg.add(Block(name=""))


def test_registries_dunder_methods() -> None:
    reg = LayerRegistry()
    reg.add(Layer(name="A"))
    reg.add(Layer(name="B"))
    assert len(reg) == 2
    assert set(iter(reg)) == {"A", "B"}