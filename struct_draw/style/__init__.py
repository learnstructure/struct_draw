"""struct_draw.style — Drawing-side style registries.

Single source of truth for layers, line types, text styles,
dimension styles, and blocks. The default registries follow
typical ACI 318 / US structural-drawing conventions and are
sufficient for most beams, columns, slabs, and footings.

All element functions pull from these registries (via the
``style/`` imports in :mod:`struct_draw.core.document`) so that a
user override propagates everywhere automatically.
"""

from struct_draw.style.layers import Layer, LayerRegistry, default_registry as default_layers
from struct_draw.style.linetypes import LineType, LineTypeRegistry, default_registry as default_linetypes
from struct_draw.style.text_styles import TextStyle, TextStyleRegistry, default_registry as default_text_styles
from struct_draw.style.dimension_styles import (
    ArrowheadKind,
    DimensionStyle,
    DimensionStyleRegistry,
    default_registry as default_dimension_styles,
)
from struct_draw.style.blocks import Block, BlockRegistry, default_registry as default_blocks

__all__ = [
    # layers
    "Layer",
    "LayerRegistry",
    "default_layers",
    # line types
    "LineType",
    "LineTypeRegistry",
    "default_linetypes",
    # text styles
    "TextStyle",
    "TextStyleRegistry",
    "default_text_styles",
    # dimension styles
    "ArrowheadKind",
    "DimensionStyle",
    "DimensionStyleRegistry",
    "default_dimension_styles",
    # blocks
    "Block",
    "BlockRegistry",
    "default_blocks",
]