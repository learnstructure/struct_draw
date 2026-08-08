"""Drawing-side constants.

These are **purely drawing-side** constants — they describe how
things look on paper (line weights, default sizes), not how
they behave structurally (material strengths, design limits).
Engineering constants belong in ``aci318`` / ``struct_core``,
not here.
"""

# DXF line-weight units are 1/100 mm.
# 0.25 mm = 25 in DXF units. Common structural-drawing values:

DEFAULT_LINEWEIGHT_100MM: int = 25         # ~0.25 mm (typical)
BOLD_LINEWEIGHT_100MM:    int = 35         # ~0.35 mm
LIGHT_LINEWEIGHT_100MM:   int = 18         # ~0.18 mm
CUT_LINEWEIGHT_100MM:     int = 50         # ~0.50 mm

# DXF color indices most commonly used in structural drawings.
# (See `struct_draw.layers.default_registry` for layer defaults.)

COLOR_REBAR:        int = 1    # red
COLOR_YELLOW:       int = 2    # yellow (splice layer default)
COLOR_GREEN:        int = 3    # green (dimensions)
COLOR_CYAN:         int = 4    # cyan (center lines, grids)
COLOR_BLUE:         int = 5    # blue (annotations / text)
COLOR_MAGENTA:      int = 6    # magenta (section cuts)
COLOR_WHITE:        int = 7    # white (concrete outline)
COLOR_GRAY:         int = 8    # gray (hatches)
COLOR_LIGHT_GRAY:   int = 252  # light gray (hidden lines)

# Plot / DXF units strings accepted by ezdxf.

UNIT_INCH:   str = "inch"
UNIT_MM:     str = "mm"
UNIT_CM:     str = "cm"
UNIT_M:      str = "m"
UNIT_FOOT:   str = "foot"

# Default paper sizes for when none is specified.

DEFAULT_SHEET_WIDTH_IN:  float = 36.0
DEFAULT_SHEET_HEIGHT_IN: float = 24.0