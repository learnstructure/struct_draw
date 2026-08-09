import ezdxf

doc = ezdxf.new("R2010")
msp = doc.modelspace()

# Add a linear dimension measuring distance between (0, 0) and (10, 0)
# dimension line is offset at y = 3
dim = msp.add_linear_dim(
    base=(0, 3),
    p1=(0, 0),
    p2=(10, 0),
    dimstyle="EZDEFAULT",
)

# Render dimension geometry before saving
dim.render()

doc.saveas("dimensions.dxf")