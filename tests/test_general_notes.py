"""The sheet's general notes state the inputs the design was made with (DesignResult.inputs), never assumed grades."""

from struct_core import AppliedDefault, ConcreteMaterial, DesignInputs, RebarMaterial, RectangularSection, parse_units

from struct_draw.elements.column import general_notes


def _inputs(defaults=()):
    rc = dict(material_id="C35", rebar_material_id="G420", transverse_rebar_material_id="G420", cover=0.05)
    return DesignInputs(
        design_code="ACI 318-19",
        materials=[ConcreteMaterial(id="C35", fc=35000.0, E=2.8e7, unit_weight=23.6),
                   RebarMaterial(id="G420", fy=420000.0, E=2.0e8)],
        sections=[RectangularSection(id="COL", b=0.5, h=0.5, **rc)],
        allowable_bearing_pressure=200.0,
        footing_cover=0.075,
        defaults_applied=list(defaults),
    )


def test_notes_state_the_design_materials_covers_and_given_bearing_pressure():
    text = "\n".join(general_notes(True, inputs=_inputs(), units=parse_units("kN, m")))
    assert "ACI 318-19" in text
    assert "f'c = 35.0 MPa (5,076 psi), NORMAL WEIGHT CONCRETE" in text
    assert "fy = 420.0 MPa (60.9 ksi)" in text
    assert "(TO OUTER TIES/STIRRUPS): 50 mm" in text and "CAST AGAINST EARTH: 75 mm" in text
    assert "200 kPa (4.2 ksf) UNDER SERVICE LOADS (DESIGN BRIEF)" in text and "PRELIMINARY" not in text
    assert "4000 psi" not in text and "27.6 MPa" not in text


def test_a_default_bearing_pressure_is_marked_preliminary():
    applied = [AppliedDefault(name="allowable_bearing_pressure", value=150.0, unit="kPa", source="assumed")]
    text = "\n".join(general_notes(False, inputs=_inputs(applied), units=parse_units("kN, m")))
    assert "PRELIMINARY" in text and "ASSUMED NET ALLOWABLE SOIL BEARING" in text
    assert "4.2 ksf (200 kPa)" in text


def test_lightweight_concrete_and_no_foundations():
    inputs = _inputs()
    inputs.materials[0] = inputs.materials[0].model_copy(update={"unit_weight": 18.0})  # about 115 pcf
    inputs.allowable_bearing_pressure = None
    text = "\n".join(general_notes(True, inputs=inputs, units=parse_units("kN, m")))
    assert "LIGHTWEIGHT CONCRETE" in text and "FOUNDATIONS: NOT DESIGNED" in text


def test_without_design_inputs_no_material_value_is_invented():
    text = "\n".join(general_notes(True, design_code="ACI 318-25"))
    assert "f'c = SEE DESIGN" in text and "fy = SEE DESIGN" in text
    assert "MPa (" not in text.split("PCC")[0]


def test_different_longitudinal_and_transverse_rebar_grades_both_reported():
    inputs = _inputs()
    inputs.materials.append(RebarMaterial(id="G280", fy=280000.0, E=2.0e8))
    inputs.sections[0] = inputs.sections[0].model_copy(update={"transverse_rebar_material_id": "G280"})
    text = "\n".join(general_notes(True, inputs=inputs, units=parse_units("kN, m")))
    assert "420.0 MPa" in text and "280.0 MPa" in text
    assert "LONGITUDINAL" in text and "TRANSVERSE" in text
