"""Tests for stub parser."""

from pathlib import Path
from freecad_lap.stubs import parse_stubs
from freecad_lap.ir import IR

FIXTURES = Path(__file__).parent / "fixtures" / "fake_freecad"


def test_parse_stubs_returns_ir():
    ir = parse_stubs(str(FIXTURES))
    assert isinstance(ir, IR)


def test_parse_finds_classes():
    ir = parse_stubs(str(FIXTURES))
    all_names = [c.name for c in ir.all_classes()]
    assert "Vector" in all_names
    assert "Document" in all_names
    assert "Shape" in all_names
    assert "Pad" in all_names
    assert "SketchObject" in all_names


def test_parse_inheritance():
    ir = parse_stubs(str(FIXTURES))
    pad = ir.namespaces["PartDesign"]["Pad"]
    assert pad.parent == "Feature"
    feature = ir.namespaces["Part"]["Feature"]
    assert feature.parent == "GeoFeature"


def test_parse_properties():
    ir = parse_stubs(str(FIXTURES))
    vector = ir.namespaces["FreeCAD"]["Vector"]
    assert "x" in vector.properties
    assert vector.properties["x"].type == "float"


def test_parse_methods():
    ir = parse_stubs(str(FIXTURES))
    shape = ir.namespaces["Part"]["Shape"]
    assert "fuse" in shape.methods
    method = shape.methods["fuse"]
    assert method.returns == "Shape"
    assert len(method.args) == 1


def test_parse_static_methods():
    ir = parse_stubs(str(FIXTURES))
    console = ir.namespaces["FreeCAD"]["Console"]
    assert "PrintMessage" in console.methods
    assert console.methods["PrintMessage"].static is True


def test_parse_enums():
    ir = parse_stubs(str(FIXTURES))
    all_enums = ir.all_enums()
    enum_names = [e.name for e in all_enums]
    assert "ShapeType" in enum_names
    assert "ConstraintType" in enum_names
    shape_type = ir.enums["Part"]["ShapeType"]
    assert "Solid" in shape_type.values


def test_parse_docstrings():
    ir = parse_stubs(str(FIXTURES))
    shape = ir.namespaces["Part"]["Shape"]
    assert shape.description == "A geometric shape."
    pad = ir.namespaces["PartDesign"]["Pad"]
    assert "pad" in pad.description.lower()
