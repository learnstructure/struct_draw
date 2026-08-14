"""struct_draw.elements — The element library.

This is the **library** that the rest of the ecosystem calls. One
module per structural member type, each exposing a small set of
``*_view`` functions that mutate an ``ezdxf.Drawing``.

Element functions are completely engineering-agnostic — they read
only :mod:`struct_draw.core.data` dataclass fields and call into
:mod:`struct_draw.core.primitives` / :mod:`struct_draw.core.composite`.

Public modules:

* :mod:`struct_draw.elements.beam` — section + elevation views
* :mod:`struct_draw.elements.beam_profile` — multi-span continuous beam profile views
* :mod:`struct_draw.elements.column` — section + elevation views
* :mod:`struct_draw.elements.footing` — plan + section views
* :mod:`struct_draw.elements.staircase` — plan + section views
* :mod:`struct_draw.elements.slab` — plan + section views
"""

from struct_draw.elements import (  # noqa: F401
    beam,
    beam_profile,
    column,
    combined_footing,
    footing,
    general_frame,
    slab,
    staircase,
)

__all__ = [
    "beam",
    "beam_profile",
    "column",
    "combined_footing",
    "footing",
    "general_frame",
    "slab",
    "staircase",
]