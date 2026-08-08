import ezdxf

# 1. Create a new DXF document
doc = ezdxf.new("R2010")

# 2. Get the modelspace (where 2D/3D drawing entities live)
msp = doc.modelspace()

# 3. Add graphical entities
# Add a line from (0, 0) to (10, 5)
msp.add_line((0, 0), (10, 5))

# Add text at coordinates (0, 6) with height 0.5
msp.add_text("Hello, ezdxf!", dxfattribs={"height": 0.5}).set_placement((0, 6))

# 4. Save the drawing
doc.saveas("simple_drawing.dxf")