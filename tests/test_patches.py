"""Tests for the patches system."""

import textwrap
from pathlib import Path

from freecad_lap.ir import IR, ClassDef, MethodDef, PropertyDef
from freecad_lap.patches import apply_patches


def test_add_gotchas(tmp_path):
    patches_file = tmp_path / "patches.yaml"
    patches_file.write_text(textwrap.dedent("""\
        gotchas:
          - "SketchObject.Support is removed in 0.19+"
    """))
    ir = IR()
    apply_patches(ir, patches_file)
    assert "SketchObject.Support is removed in 0.19+" in ir.gotchas


def test_duplicate_gotcha_not_added(tmp_path):
    patches_file = tmp_path / "patches.yaml"
    patches_file.write_text(textwrap.dedent("""\
        gotchas:
          - "already here"
    """))
    ir = IR()
    ir.gotchas = ["already here"]
    apply_patches(ir, patches_file)
    assert ir.gotchas.count("already here") == 1


def test_add_class_property(tmp_path):
    patches_file = tmp_path / "patches.yaml"
    patches_file.write_text(textwrap.dedent("""\
        classes:
          SketchObject:
            add_properties:
              AttachmentSupport:
                type: PropertyLinkSubList
                description: "The support plane"
    """))
    ir = IR()
    ir.add_class(ClassDef(name="SketchObject", namespace="Sketcher"))
    apply_patches(ir, patches_file)
    cls = ir.namespaces["Sketcher"]["SketchObject"]
    assert "AttachmentSupport" in cls.properties
    assert cls.properties["AttachmentSupport"].type == "PropertyLinkSubList"


def test_remove_class_property(tmp_path):
    patches_file = tmp_path / "patches.yaml"
    patches_file.write_text(textwrap.dedent("""\
        classes:
          SketchObject:
            remove_properties:
              - Support
    """))
    ir = IR()
    ir.add_class(ClassDef(
        name="SketchObject",
        namespace="Sketcher",
        properties={"Support": PropertyDef(name="Support", type="PropertyLinkSub")},
    ))
    apply_patches(ir, patches_file)
    cls = ir.namespaces["Sketcher"]["SketchObject"]
    assert "Support" not in cls.properties


def test_no_patches_file(tmp_path):
    ir = IR()
    apply_patches(ir, tmp_path / "nonexistent.yaml")
    assert ir.gotchas == []


def test_create_class_from_patch(tmp_path):
    patches_file = tmp_path / "patches.yaml"
    patches_file.write_text(textwrap.dedent("""\
        classes:
          NewClass:
            description: "A new class added by patch"
    """))
    ir = IR()
    apply_patches(ir, patches_file)
    cls = ir.namespaces["FreeCAD"]["NewClass"]
    assert cls.description == "A new class added by patch"
