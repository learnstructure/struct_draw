import ezdxf
from ezdxf import colors, linetypes

doc = ezdxf.new("R2010")

# Setup custom linetypes if needed
doc.linetypes.add("DASHED", pattern=[0.5, 0.25, -0.25])

# 1. Add layers with specific attributes
doc.layers.add(
    name="OUTLINE",
    color=colors.RED,
    lineweight=30,  # Line weight in hundredths of a millimeter (0.30 mm)
)

doc.layers.add(
    name="HIDDEN_LINES",
    color=colors.CYAN,
    linetype="DASHED",
)

doc.layers.add(
    name="ANNOTATIONS",
    color=colors.GREEN,
)

# 2. Assign entities to created layers
msp = doc.modelspace()

msp.add_circle((0, 0), radius=10, dxfattribs={"layer": "OUTLINE"})
msp.add_line((-15, 0), (15, 0), dxfattribs={"layer": "HIDDEN_LINES"})
msp.add_text(
    "Radius = 10", dxfattribs={"layer": "ANNOTATIONS", "height": 1}
).set_placement((0, 12))

doc.saveas("layers_setup.dxf")