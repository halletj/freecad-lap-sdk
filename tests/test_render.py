"""Tests for LAP renderer."""

from freecad_lap.ir import IR, ClassDef, MethodDef, PropertyDef, EnumDef
from freecad_lap.render import render_domain, render_graph, render_gotchas


def _make_test_ir():
    ir = IR()
    ir.add_class(ClassDef(
        name="Document",
        namespace="FreeCAD",
        description="A FreeCAD document.",
        properties={
            "Name": PropertyDef(name="Name", type="str", description="The document name."),
        },
        methods={
            "addObject": MethodDef(
                name="addObject",
                args=[("type", "str"), ("name", "str")],
                returns="DocumentObject",
            ),
            "recompute": MethodDef(name="recompute", returns="None"),
        },
    ))
    ir.add_class(ClassDef(
        name="Pad",
        namespace="PartDesign",
        parent="Feature",
        description="A pad feature.",
        properties={
            "Length": PropertyDef(name="Length", type="float"),
            "Profile": PropertyDef(name="Profile", type="DocumentObject"),
        },
        methods={
            "execute": MethodDef(name="execute", returns="None"),
        },
    ))
    ir.add_class(ClassDef(
        name="Pocket",
        namespace="PartDesign",
        parent="Feature",
        description="A pocket feature.",
        properties={
            "Length": PropertyDef(name="Length", type="float"),
        },
    ))
    ir.add_enum(EnumDef(
        name="ShapeType",
        namespace="Part",
        values=["Solid", "Shell", "Face"],
    ))
    ir.gotchas = ["ALWAYS call doc.recompute() after modifying objects"]
    return ir


def test_render_domain_contains_classes():
    ir = _make_test_ir()
    output = render_domain(ir, "partdesign", ["Pad*", "Pocket*"])
    assert "Pad : Feature" in output
    assert "Length: float" in output
    assert "execute() -> None" in output


def test_render_domain_contains_enums():
    ir = _make_test_ir()
    output = render_domain(ir, "part", ["Shape*", "ShapeType"])
    assert "ShapeType:" in output
    assert "Solid" in output


def test_render_graph():
    ir = _make_test_ir()
    output = render_graph(ir)
    assert "[graph]" in output
    assert "FreeCAD" in output
    assert "Document" in output


def test_render_gotchas():
    ir = _make_test_ir()
    output = render_gotchas(ir)
    assert "[gotchas]" in output
    assert "recompute" in output
