"""Tests for the intermediate representation module."""

from freecad_lap.ir import IR, ClassDef, MethodDef, PropertyDef, EnumDef


def test_create_empty_ir():
    ir = IR()
    assert ir.namespaces == {}


def test_add_class():
    ir = IR()
    cls = ClassDef(
        name="Vector",
        namespace="FreeCAD",
        description="A 3D vector.",
        properties={
            "x": PropertyDef(name="x", type="float", description="The x coordinate."),
        },
        methods={
            "add": MethodDef(
                name="add",
                args=[("other", "Vector")],
                returns="Vector",
                description="Add another vector.",
            ),
        },
    )
    ir.add_class(cls)
    assert "FreeCAD" in ir.namespaces
    assert "Vector" in ir.namespaces["FreeCAD"]


def test_add_enum():
    ir = IR()
    enum = EnumDef(
        name="ShapeType",
        namespace="Part",
        values=["Solid", "Shell", "Face", "Wire", "Edge", "Vertex"],
    )
    ir.add_enum(enum)
    assert "ShapeType" in ir.enums["Part"]


def test_merge_enriches_existing_class():
    ir = IR()
    cls = ClassDef(name="Pad", namespace="PartDesign", parent="Feature")
    ir.add_class(cls)

    enrichment = ClassDef(
        name="Pad",
        namespace="PartDesign",
        description="A pad (extrusion) feature.",
        properties={
            "Length": PropertyDef(name="Length", type="float", description="The length of the pad."),
        },
    )
    ir.merge_class(enrichment)

    merged = ir.namespaces["PartDesign"]["Pad"]
    assert merged.description == "A pad (extrusion) feature."
    assert "Length" in merged.properties
    assert merged.parent == "Feature"  # preserved from original


def test_all_classes():
    ir = IR()
    ir.add_class(ClassDef(name="Vector", namespace="FreeCAD"))
    ir.add_class(ClassDef(name="Shape", namespace="Part"))
    all_classes = ir.all_classes()
    names = [c.name for c in all_classes]
    assert "Vector" in names
    assert "Shape" in names
