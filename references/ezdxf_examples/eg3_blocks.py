import ezdxf

doc = ezdxf.new("R2010")

# 1. Create a Block Definition
door_block = doc.blocks.new(name="DOOR_SYMBOL")

# Draw the geometry inside the block (relative to block origin (0, 0))
door_block.add_line((0, 0), (0, 3))
door_block.add_arc(
    center=(0, 0), radius=3, start_angle=0, end_angle=90
)

# 2. Insert instances into the Modelspace
msp = doc.modelspace()

# Place a door at (10, 20) with rotation
msp.add_blockref("DOOR_SYMBOL", insert=(10, 20), dxfattribs={"rotation": 45})

# Place another door at (30, 20) with scaling
msp.add_blockref(
    "DOOR_SYMBOL",
    insert=(30, 20),
    dxfattribs={"xscale": 1.5, "yscale": 1.5},
)

doc.saveas("blocks_example.dxf")