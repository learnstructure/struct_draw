"""struct_draw.adapters — Producer-result → struct_draw dataclass adapters.

Adapters are the **only** place in ``struct_draw`` that knows about
producer schemas. They read ``DesignResult`` / ``DetailingResult``
objects produced by ``aci318`` (and any future engineering
packages) and translate them into the plain
:mod:`struct_draw.core.data` dataclasses that the element
library consumes.

Adapters never draw anything and never import ``ezdxf``.
"""

from struct_draw.adapters import aci318  # noqa: F401

__all__ = ["aci318"]