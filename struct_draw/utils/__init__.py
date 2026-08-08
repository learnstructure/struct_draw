"""struct_draw.utils — Reusable helpers, exceptions, and constants.

Modules:

- :mod:`struct_draw.utils.exceptions` — the ``struct_draw``
  exception hierarchy.
- :mod:`struct_draw.utils.geometry` — pure 2D geometry helpers
  (bounding boxes, transforms, intersection tests). **No
  engineering calculations.**
- :mod:`struct_draw.utils.constants` — drawing-side constants
  (default paper sizes, default line weights in 1/100 mm).
"""

from struct_draw.utils.exceptions import (
    BackendError,
    DrawError,
    RegistryError,
    StructDrawError,
)

__all__ = [
    "StructDrawError",
    "BackendError",
    "DrawError",
    "RegistryError",
]