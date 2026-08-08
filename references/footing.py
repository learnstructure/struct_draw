from pyautocad import Autocad, APoint, types
import math


acad = Autocad()  # create_if_not_exists=True

doc = acad.ActiveDocument
print(doc.Name)
ms = doc.ModelSpace

# Level
foot_id = 2
col = [350, 350]
p_beam = [230, 350]
f_beam = [230, 300]
ledge = 100
footing = {"len": 1600, "wid": 1600, "mid_thick": 400, "edge_thick": 200}
depth = {"pl": 600, "fd": 1500}
bar_dia = 12

# define layers
found_lay = doc.Layers.Add("Foundation")
found_lay.Color = 105
column_lay = doc.Layers.Add("Column")
column_lay.Color = 5
beam_layer = doc.Layers.Add("Beam")
beam_layer.Color = 10
rebar_layer = doc.Layers.Add("Rebar")
rebar_layer.Color = 2
rebar_layer_hatch = doc.Layers.Add("Rebar_hatch")
rebar_layer_hatch.Color = 2
rebar_layer_hatch.Lineweight = 50.0  # 0.5 line weight

dim_layer = doc.Layers.Add("Dimension")
dim_layer.Color = 132

stirrup_layer = doc.Layers.Add("Stirrup")
stirrup_layer.Color = 135
text_layer = doc.Layers.Add("Text")
text_layer.Color = 151

level_layer = doc.Layers.Add("Level")
level_layer.Color = 8

cen_layer = doc.Layers.Add("CEN")
cen_layer.Color = 132


def lineWithLayer(p1, p2, layer_name):
    "Point1, Point2 and a layer"
    line0 = ms.AddLine(p1, p2)
    line0.layer = layer_name
    return line0


def circleWithLayer(center, radius, layer_name):
    "Point1, radius and a layer"
    circle1 = ms.AddCircle(center, radius)
    circle1.layer = layer_name
    return circle1


def copy(line, p):
    dx, dy = p.x - line.StartPoint[0], p.y - line.StartPoint[1]
    StartPoint = APoint(line.StartPoint[0] + dx, line.StartPoint[1] + dy)
    EndPoint = APoint(line.EndPoint[0] + dx, line.EndPoint[1] + dy)
    new_line = ms.AddLine(StartPoint, EndPoint)
    new_line.layer = line.layer
    return new_line


def addDimension(
    p1, p2, size, layer=1
):  # https://help.autodesk.com/view/OARX/2023/ENU/?guid=GUID-FE41C4DC-4717-41AC-9C07-6531CB9332E2
    if p1.y == p2.y:
        p3 = (p1 + p2) / 2 - APoint(0, 200 * layer)
        dim = ms.AddDimAligned(p1, p2, p3)
    else:
        p3 = (p1) - APoint(200 * layer, 0)
        p1 = acad.aDouble(p1.x, p1.y, 0)
        p2 = acad.aDouble(p2.x, p2.y, 0)
        p3 = acad.aDouble(p3.x, p3.y, 0)
        dim = ms.AddDimRotated(p1, p2, p3, 90 * math.pi / 180)

    dim.layer = "Dimension"
    dim.TextHeight = size
    dim.ArrowHeadSize = 50
    dim.ExtLineFixedLenSuppress = True
    dim.ExtLineFixedLen = 50
    dim.ExtensionLineExtend = 50
    dim.Fit
    dim.TextGap = 10
    dim.SuppressTrailingZeros = True
    dim.VerticalTextPosition = 3
    dim.TextInsideAlign = False
    return dim


def addText(text, point, size):
    "Text, point and size"
    text1 = ms.AddText(text, point, size)
    text1.layer = "Text"
    return text1


def add_polyline(points_list, layer):
    "add_polyline(points_list,layer)"
    points = acad.aDouble()
    for point in points_list:
        points.append(point.x)
        points.append(point.y)
        points.append(0)
    line0 = ms.AddPolyline(points)
    line0.layer = layer
    return line0


p1 = APoint(-footing["len"] / 2, 0)
p2 = APoint(footing["len"] / 2, 0)
line1 = lineWithLayer(p1, p2, "Foundation")


txt1 = addText(f"Section of F{foot_id} at X{foot_id} ", APoint(-550, -650), 130)

p3 = APoint(p1.x, p1.y + footing["edge_thick"])
line2 = lineWithLayer(p1, p3, "Foundation")

add_polyline([p1, p1 - APoint(0, 75), p2 - APoint(0, 75), p2], "Foundation")
add_polyline(
    [p1 - APoint(0, 75), p1 - APoint(0, 150), p2 - APoint(0, 150), p2 - APoint(0, 75)],
    "Foundation",
)
copy(line2, p2)

p4 = APoint(-col[0] / 2 - ledge, footing["mid_thick"])
line3 = lineWithLayer(APoint(p3.x, p3.y), p4, "Foundation")
p5 = p4 + APoint(ledge, 0)
line4 = lineWithLayer(p4, p5, "Foundation")
ext_top = 400
p6 = p5 + APoint(0, depth["fd"] + depth["pl"] - footing["mid_thick"] + ext_top)
line5 = lineWithLayer(p5, p6, "Column")  # column line

p_GL = APoint(-col[0] / 2, depth["fd"])
p_PL = APoint(-col[0] / 2, depth["fd"] + depth["pl"])
line_GL = lineWithLayer(p_GL, p_GL - APoint(700, 0), "Level")
line_PL = lineWithLayer(p_PL, p_PL - APoint(700, 0), "Level")
p7 = APoint(-footing["len"] / 2 + 70, 50)
p8 = APoint(footing["len"] / 2 - 70, 50)

line2.Mirror(APoint(0, 0), APoint(0, footing["mid_thick"]))
line3.Mirror(APoint(0, 0), APoint(0, footing["mid_thick"]))
line4.Mirror(APoint(0, 0), APoint(0, footing["mid_thick"]))
line5.Mirror(APoint(0, 0), APoint(0, footing["mid_thick"]))

ln_bar = lineWithLayer(p7, p8, "Rebar")
ln_bar1 = lineWithLayer(p7, APoint(p7.x, p7.y + 80), "Rebar")
ln_bar1.Mirror(APoint(0, 0), APoint(0, footing["mid_thick"]))

p9 = APoint(p7.x + 10, p7.y + 10)
spacing = 100
n_bot_bar = int((p8.x - p7.x) / spacing)
spacing_i = 0
for i in range(n_bot_bar + 1):
    spacing_i = i * spacing
    circleWithLayer(APoint(p7.x + 10 + spacing_i, p7.y + 10), 7, "Rebar_hatch")
# circle = ms.AddCircle(p9, 7)

line6 = lineWithLayer(
    APoint(0, 85), p6 + APoint(col[0] / 2, 0), "Rebar"
)  # central longitudinal bar
line7 = copy(line6, APoint(-col[0] / 2 + 50, 85))
line8 = copy(line6, APoint(col[0] / 2 - 50, 85))
pcf1 = APoint(-footing["len"] * 0.35, 85)
line9 = lineWithLayer(
    pcf1, APoint(+footing["len"] * 0.35, 85), "Rebar"
)  # line9 is column bar into the footing
ml1 = add_polyline(
    [
        p5 - APoint(0, 50),
        p5 - APoint(20, 50),
        p5,
        p5 + APoint(20, -50),
        p5 - APoint(0, 50),
        p5 - APoint(0, footing["mid_thick"] - 130),
        pcf1 + APoint(+50, 45),
        pcf1 + APoint(+50, 25),
        pcf1 + APoint(0, 45),
        pcf1 + APoint(+50, 65),
        pcf1 + APoint(+50, 45),
    ],
    "Dimension",
)  # Ld description
addText("Ld", p5 - APoint(130, footing["mid_thick"] - 150), 80)
p10 = APoint(line9.StartPoint[0], line9.StartPoint[1])
line10 = copy(ln_bar1, p10)
copy(line10, APoint(line9.EndPoint[0], line9.EndPoint[1]))

stirrup = lineWithLayer(
    APoint(-col[0] / 2 + 40, 100), APoint(col[0] / 2 - 40, 100), "Stirrup"
)
n_stirrup = int((depth["fd"] + depth["pl"] + ext_top) / spacing)
for i in range(n_stirrup - 1):
    lineWithLayer(
        APoint(-col[0] / 2 + 40, 100 + i * spacing),
        APoint(col[0] / 2 - 40, 100 + i * spacing),
        "Stirrup",
    )

bp_x = -col[0] / 2 - 100
bp_y = depth["fd"] + depth["pl"] + ext_top
break_line_points = acad.aDouble(
    bp_x,
    bp_y,
    0,
    -30,
    bp_y,
    0,
    0,
    bp_y + 50,
    0,
    0,
    bp_y - 50,
    0,
    30,
    bp_y,
    0,
    -bp_x,
    bp_y,
    0,
)

break_line = acad.model.AddPolyLine(break_line_points)

dim_fb = addDimension(p1, p2, 100, 1.5)
dim_et = addDimension(p1, p3, 70)
dim_mt = addDimension(p1, p5, 100, 2)
dim_fd = addDimension(p1, p_GL, 100, 3)
dim_pl = addDimension(p_GL, p_PL, 100, 5)
txt_gl = addText("Ground Lvl.", p_GL - APoint(750, -50), 100)
txt_pl = addText("Plinth Lvl.", p_PL - APoint(700, -50), 100)


def addRectangle(p1, p2, layer):
    "First corner and third corner points"
    points = acad.aDouble(
        p1.x, p1.y, 0, p1.x, p2.y, 0, p2.x, p2.y, 0, p2.x, p1.y, 0, p1.x, p1.y, 0
    )
    rect0 = ms.AddPolyline(points)
    rect0.layer = layer
    return rect0


p_plan_cent = APoint(0, depth["fd"] + depth["pl"] + ext_top + footing["len"] / 2 + 800)
col_corner1 = p_plan_cent - APoint(col[0] / 2, col[1] / 2)
col_corner2 = p_plan_cent + APoint(col[0] / 2, col[1] / 2)
rect_col = addRectangle(col_corner1, col_corner2, "Column")
ledge_1 = col_corner1 - APoint(ledge, ledge)
ledge_2 = col_corner2 + APoint(ledge, ledge)
rect_ledge = addRectangle(ledge_1, ledge_2, "Foundation")
foot_1 = p_plan_cent - APoint(footing["len"] / 2, footing["wid"] / 2)
foot_2 = p_plan_cent + APoint(footing["len"] / 2, footing["wid"] / 2)
foot_p = addRectangle(foot_1, foot_2, "Foundation")

lf1 = lineWithLayer(ledge_1, foot_1, "Foundation")
lf1.Mirror(p_plan_cent, p_plan_cent + APoint(50, 0))
lf3 = lineWithLayer(ledge_2, foot_2, "Foundation")
lf3.Mirror(p_plan_cent, p_plan_cent + APoint(50, 0))

addDimension(foot_1, foot_1 + APoint(footing["len"], 0), 100)
addDimension(foot_1, foot_1 + APoint(0, footing["wid"]), 100)
addDimension(col_corner2, col_corner2 - APoint(0, col[1]), 70, -1)
addDimension(ledge_2, ledge_2 - APoint(0, col[1] + 2 * ledge), 70, -1.5)
ledge_dim = addDimension(p4, p5, 80, -0.5)
ledge_dim.HorizontalTextPosition = 1

addText(f"Plan of F{foot_id}", foot_1 - APoint(-100, 450), 100)

p_slabel = p_plan_cent - APoint(footing["len"] / 2 + 500, 0)
l_slabel = add_polyline(
    [
        p_plan_cent,
        p_slabel - APoint(75, 0),
        p_slabel + APoint(0, 75),
        p_slabel + APoint(75, 0),
    ],
    "CEN",
)
l_slabel.Mirror(p_plan_cent, p_plan_cent + APoint(0, 100))
addText(f"X{foot_id}", p_slabel + APoint(-75, 90), 80)
f1_text = addText(f"F{foot_id}", ledge_2 + APoint(-10, 200), 90)
f1_text.Color = 3


def addRebar(p1, p2, layer):
    "First & second points with layer"
    if p1.y == p2.y:
        p1 = p1 + APoint(60, 150)
        p2 = p2 + APoint(-60, 150)
        p3 = p1 + APoint(0, 100)
        p4 = p2 + APoint(0, 100)
    else:
        p1 = p1 + APoint(150, 60)
        p2 = p2 + APoint(150, -60)
        p3 = p1 + APoint(100, 0)
        p4 = p2 + APoint(100, 0)
    points = acad.aDouble(p3.x, p3.y, 0, p1.x, p1.y, 0, p2.x, p2.y, 0, p4.x, p4.y, 0)
    line0 = ms.AddPolyline(points)
    line0.layer = layer
    dim_rebar = addDimension(p1, p2, 60, -1)
    dim_rebar.TextOverride = f"{bar_dia}φ @ 150mm c/c"

    return line0


addRebar(foot_1, foot_1 + APoint(footing["len"], 0), "Rebar")
addRebar(foot_1, foot_1 + APoint(0, footing["wid"]), "Rebar")


def add_mleader(p1, p2, p3, text):
    leader0 = ms.AddMLeader(
        acad.aDouble(p1.x, p1.y, 0, p2.x, p2.y, 0, p3.x, p3.y, 0), 1
    )
    leader0.ArrowheadSize = 50
    leader0.TextHeight = 90
    leader0.TextString = text
    leader0.layer = "Text"
    return leader0


# rebar leader
text_bar = f"{bar_dia}φ @ 150mm c/c \nbothways"
bar_p1 = APoint(col[0], 70)
bar_p2 = APoint(col[0] + 150, footing["mid_thick"] + 100)
bar_p3 = APoint(col[0] + 200, footing["mid_thick"] + 100)
bar_leader = add_mleader(bar_p1, bar_p2, bar_p3, text_bar)
bar_leader.AddLeaderLineEx(
    acad.aDouble(
        bar_p1.x + 200, bar_p1.y, 0, bar_p2.x, bar_p2.y, 0, bar_p3.x, bar_p3.y, 0
    )
)

text_col = f"Column {col[0]}x{col[1]}"
col_p1 = APoint(col[0] / 2, depth["fd"] + depth["pl"] + 200)
col_p2 = APoint(col[0] / 2 + 100, depth["fd"] + depth["pl"] + 300)
col_p3 = APoint(col[0] / 2 + 150, depth["fd"] + depth["pl"] + 300)
col_leader = add_mleader(col_p1, col_p2, col_p3, text_col)

text_ring = f"8φ @ 100mm c/c \ncolumn stirrups"
ring_p1 = APoint(col[0] / 2 - 100, footing["mid_thick"] + 700)
ring_p2 = APoint(col[0] / 2 + 100, footing["mid_thick"] + 900)
ring_p3 = APoint(col[0] / 2 + 150, footing["mid_thick"] + 900)
ring_leader = add_mleader(ring_p1, ring_p2, ring_p3, text_ring)

text_fb = f"Foundation Beam\n{f_beam[0]}x{f_beam[1]}"
fb_p1 = APoint(100, footing["mid_thick"] + 200)
fb_p2 = APoint(col[0] / 2 + 100, footing["mid_thick"] + 500)
fb_p3 = APoint(col[0] / 2 + 150, footing["mid_thick"] + 500)
fb_leader = add_mleader(fb_p1, fb_p2, fb_p3, text_fb)

text_pb = f"Plinth Beam\n{p_beam[0]}x{p_beam[1]}"
pb_p1 = APoint(100, depth["fd"] + depth["pl"] - 200)
pb_p2 = APoint(col[0] / 2 + 150, depth["fd"] + depth["pl"])
pb_p3 = APoint(col[0] / 2 + 200, depth["fd"] + depth["pl"])
pb_leader = add_mleader(pb_p1, pb_p2, pb_p3, text_pb)

text_pcc = "75 mm thick M10 PCC"
pcc_p1 = APoint(footing["len"] / 3, -30)
pcc_p2 = APoint(footing["len"] / 3, -200)
pcc_p3 = APoint(footing["len"] / 3 + 300, -200)
pcc_leader = add_mleader(pcc_p1, pcc_p2, pcc_p3, text_pcc)
pcc_leader.ArrowheadSize = 30
text_sol = "One flat brick soling"
sol_leader = add_mleader(
    pcc_p1 - APoint(0, 75), pcc_p2 - APoint(0, 200), pcc_p3 - APoint(0, 200), text_sol
)
sol_leader.ArrowheadSize = 30


def beam_block(name, width, depth):
    block_name = f"{name}{width}x{depth}"
    insert_point = APoint(0, 0)

    # plinth beam and foundation beam
    block_def = acad.doc.Blocks.Add(insert_point, block_name)
    r1 = block_def.AddPolyline(
        acad.aDouble(
            -width / 2,
            0,
            0,
            width / 2,
            0,
            0,
            width / 2,
            -depth,
            0,
            -width / 2,
            -depth,
            0,
            -width / 2,
            0,
            0,
        )
    )
    r2 = block_def.AddPolyline(
        acad.aDouble(
            -width / 2 + 25,
            -25,
            0,
            width / 2 - 25,
            -25,
            0,
            width / 2 - 25,
            -depth + 25,
            0,
            -width / 2 + 25,
            -depth + 25,
            0,
        )
    )
    r2.Closed = True

    r1.layer = "Beam"
    r2.layer = "Stirrup"
    c1 = block_def.AddCircle(APoint(-width / 2 + 33, -33, 0), 5)
    c2 = block_def.AddCircle(APoint(0, -33, 0), 5)
    c3 = block_def.AddCircle(APoint(width / 2 - 33, -33, 0), 5)
    c4 = block_def.AddCircle(APoint(-width / 2 + 33, -depth + 33, 0), 5)
    c5 = block_def.AddCircle(APoint(0, -depth + 33, 0), 5)
    c6 = block_def.AddCircle(APoint(width / 2 - 33, -depth + 33, 0), 5)
    c1.layer = "Rebar_hatch"
    c2.layer = "Rebar_hatch"
    c3.layer = "Rebar_hatch"
    c4.layer = "Rebar_hatch"
    c5.layer = "Rebar_hatch"
    c6.layer = "Rebar_hatch"
    l1 = block_def.AddLine(
        APoint(width / 2 - 33, -25, 0), APoint(width / 2 - 33 - 40, -25 - 40, 0)
    )
    l2 = block_def.AddLine(
        APoint(width / 2 - 25, -33, 0), APoint(width / 2 - 25 - 40, -33 - 40, 0)
    )
    l1.layer = "Stirrup"
    l2.layer = "Stirrup"
    return block_name


# Insert the block into the current drawing
acad.model.InsertBlock(
    APoint(0, depth["fd"] + depth["pl"]),
    beam_block("pb", p_beam[0], p_beam[1]),
    1,
    1,
    1,
    0,
)
acad.model.InsertBlock(
    APoint(0, footing["mid_thick"] + f_beam[1]),
    beam_block("fb", f_beam[0], f_beam[1]),
    1,
    1,
    1,
    0,
)