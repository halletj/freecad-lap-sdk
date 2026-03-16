"""Tests for enrichment (merging stubs + scraped wiki docs)."""

from freecad_lap.enrich import enrich_ir
from freecad_lap.ir import IR, ClassDef, MethodDef, PropertyDef


def test_enrich_adds_descriptions():
    ir = IR()
    ir.add_class(ClassDef(
        name="Pad",
        namespace="PartDesign",
        parent="Feature",
        methods={"execute": MethodDef(name="execute", returns="None")},
        properties={"Length": PropertyDef(name="Length", type="float")},
    ))

    scraped = {
        "Pad": ClassDef(
            name="Pad",
            description="A pad (extrusion) feature.",
            methods={"execute": MethodDef(name="execute", description="Recomputes the pad feature.")},
            properties={"Length": PropertyDef(name="Length", description="The length of the pad.")},
        ),
    }

    enrich_ir(ir, scraped)

    cls = ir.namespaces["PartDesign"]["Pad"]
    assert cls.description == "A pad (extrusion) feature."
    assert cls.methods["execute"].description == "Recomputes the pad feature."
    assert cls.methods["execute"].returns == "None"
    assert cls.properties["Length"].description == "The length of the pad."
    assert cls.properties["Length"].type == "float"


def test_enrich_adds_new_classes_from_docs():
    ir = IR()
    scraped = {
        "NewClass": ClassDef(
            name="NewClass",
            description="Found in docs but not stubs.",
        ),
    }

    enrich_ir(ir, scraped)

    all_names = [c.name for c in ir.all_classes()]
    assert "NewClass" in all_names
