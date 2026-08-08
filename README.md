# struct_draw — Drawing Generation for the Structural Engineering Ecosystem

`struct_draw` is the dedicated **drawing generation** package of the
[Structural Engineering Ecosystem](../agent.md).

It is **not** an engineering library. It does **not** perform finite
element analysis, structural dynamics, or reinforced concrete design.
It does **not** decide bar sizes, splice lengths, hook geometry, or
any other engineering content.

`struct_draw` consumes **`DesignResult`** + **`DetailingResult`** from
[`aci318`](../aci318/agent.md) (and any future schema-defined result
objects) and renders them into drawing files using drawing-side
concepts: layers, line types, text styles, dimension styles, blocks,
viewports, and sheets.

First-class output format: **DXF** (via [`ezdxf`](https://ezdxf.mozman.at/)).
PDF / IFC / SVG planned.

## Installation

```bash
pip install -r requirements.txt
pip install -e .
```

## Quick Start

```python
from struct_draw.adapters import from_struct_draw_inputs
from struct_draw.results import DrawingRequest
import struct_draw

# Suppose you have:
#   design     — a DesignResult      from aci318
#   detailing  — a DetailingResult   from aci318
#   geometry   — a StructuralModel from struct_core
#   style      — a DrawingStyle (layer/line-type/text/dimension registry)

request = DrawingRequest(
    design=design,
    detailing=detailing,
    geometry=geometry,
    style=style,
)

inputs = from_struct_draw_inputs(request)
drawing = struct_draw.render(inputs)              # returns DrawingResult
drawing.save("beam.dxf")
```

## Package Structure

```
struct_draw/
├── core/                  # Shared types: DrawingInputs, DrawingStyle, DrawingResult, enums
├── layers/                # Layer definitions and registry
├── linetypes/             # Line-type definitions and registry
├── text_styles/           # Text-style definitions and registry
├── dimension_styles/      # Dimension-style definitions and registry
├── blocks/                # Reusable DXF blocks (rebar symbols, section cuts)
├── viewports/             # Viewport layouts (plan / elevation / section / detail)
├── sheets/                # Sheet composition (title block, schedule layout)
├── plot_styles/           # Plot styles and color tables
├── backends/              # Drawing-format backends (dxf.py via ezdxf)
├── adapters/              # Adapters consuming DesignResult + DetailingResult
├── results/               # DrawingResult dataclasses
├── reports/               # Drawing-list / schedule reports
├── utils/                 # Geometry helpers, exceptions, units
├── examples/              # Worked examples
├── tests/                 # Unit + snapshot tests
└── docs/                  # User documentation
```

See [`agent.md`](./agent.md) for the full architecture, design
principles, and contribution rules.