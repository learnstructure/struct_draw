"""struct_draw exception hierarchy.

All exceptions raised by ``struct_draw`` inherit from
:class:`StructDrawError`. This lets callers catch every
struct_draw-originated exception with a single ``except`` clause
while still being able to specialize by sub-exception type.
"""

from __future__ import annotations


class StructDrawError(Exception):
    """Base class for all exceptions raised by ``struct_draw``."""


class BackendError(StructDrawError):
    """Raised when a backend cannot complete rendering.

    Examples:
        * DXF backend is missing the ``ezdxf`` package.
        * An unsupported entity kind is encountered.
        * A required geometry field is missing from a DrawEntity.
    """


class DrawError(StructDrawError):
    """Raised when the draw-pipeline cannot construct a valid output.

    Examples:
        * Trying to save a DrawingResult whose format has no
          backend.
        * An adapter received an incompatible input type.
    """


class RegistryError(StructDrawError):
    """Raised when a registry operation fails.

    Examples:
        * Adding a Layer / LineType / TextStyle with an empty name.
        * Looking up a missing name with ``require()``.
    """