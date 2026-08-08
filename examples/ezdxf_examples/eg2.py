import ezdxf
from ezdxf import colors

doc = ezdxf.new("R2010")

# Create custom layers with predefined colors
doc.layers.add("OUTLINE", color=colors.RED)
doc.layers.add("CENTERLINES", color=colors.CYAN)

msp = doc.modelspace()

# Add a circle assigned to the 'OUTLINE' layer
msp.add_circle(center=(5, 5), radius=3, dxfattribs={"layer": "OUTLINE"})

# Add a polyline (connected lines) on the 'CENTERLINES' layer
points = [(0, 5), (10, 5), (5, 10), (0, 5)]
msp.add_polyline2d(points, dxfattribs={"layer": "CENTERLINES"})

doc.saveas("shapes_and_layers.dxf")