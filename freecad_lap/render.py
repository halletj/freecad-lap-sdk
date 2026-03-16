"""Render IR into .lap format files."""

import fnmatch
import logging

from .ir import IR, ClassDef, EnumDef

logger = logging.getLogger(__name__)


def render_domain(ir: IR, domain_name: str, patterns: list[str]) -> str:
    """Render all classes/enums matching patterns into a .lap domain file."""
    lines = [f"# freecad-{domain_name}.lap", ""]

    matching_enums = []
    for enum in ir.all_enums():
        if _matches_any(enum.name, patterns):
            matching_enums.append(enum)

    matching_classes = []
    for cls in ir.all_classes():
        if _matches_any(cls.name, patterns):
            matching_classes.append(cls)

    if matching_enums:
        lines.append("[types]")
        for enum in sorted(matching_enums, key=lambda e: e.name):
            lines.append(f"{enum.name}: {' | '.join(enum.values)}")
        lines.append("")

    if matching_classes:
        lines.append("[classes]")
        for cls in sorted(matching_classes, key=lambda c: c.name):
            lines.extend(_render_class(cls))
            lines.append("")

    return "\n".join(lines)


def render_graph(ir: IR) -> str:
    """Render the [graph] section showing FreeCAD object navigation."""
    lines = ["# freecad-graph.lap", "", "[graph]"]

    # FreeCAD's graph is different from Fusion -- build from known structure
    # plus any Document/Application classes found in IR
    lines.append("FreeCAD (App)")
    lines.append("  .ActiveDocument -> Document")
    lines.append("  .newDocument(name: str) -> Document")
    lines.append("  .openDocument(path: str) -> Document")
    lines.append("  .Console -> Console")
    lines.append("  .Vector(x, y, z) -> Vector")
    lines.append("  .Placement(pos, rot) -> Placement")
    lines.append("  .Rotation(axis, angle) -> Rotation")
    lines.append("")
    lines.append("Document")
    lines.append("  .Objects -> list[DocumentObject]")
    lines.append("  .addObject(type: str, name: str) -> DocumentObject")
    lines.append("  .removeObject(name: str) -> None")
    lines.append("  .recompute() -> None")
    lines.append("  .getObject(name: str) -> DocumentObject")
    lines.append("  .save() -> None")
    lines.append("  .saveAs(path: str) -> None")
    lines.append("")
    lines.append("App::Part (spatial container)")
    lines.append("  .addObject(obj) -> None")
    lines.append("  .Group -> list[DocumentObject]")
    lines.append("  .Origin -> Origin")
    lines.append("")
    lines.append("PartDesign::Body (single solid)")
    lines.append("  .newObject(type: str, name: str) -> DocumentObject")
    lines.append("  .Tip -> Feature")
    lines.append("  .BaseFeature -> Feature")
    lines.append("  .Origin -> Origin")
    lines.append("  .Group -> list[DocumentObject]")
    lines.append("")
    lines.append("Sketcher::SketchObject")
    lines.append("  .addGeometry(geo: Part.Geometry, construction: bool) -> int")
    lines.append("  .addConstraint(constraint: Sketcher.Constraint) -> int")
    lines.append("  .Support -> PropertyLinkSub  # the plane")
    lines.append("  .MapMode -> str")
    lines.append("")
    lines.append("Part.Shape (TopoShape)")
    lines.append("  .Faces -> list[Face]")
    lines.append("  .Edges -> list[Edge]")
    lines.append("  .Vertexes -> list[Vertex]")
    lines.append("  .Wires -> list[Wire]")
    lines.append("  .Shells -> list[Shell]")
    lines.append("  .Solids -> list[Solid]")

    # Also add properties from Application class if found in IR
    app_cls = None
    for cls in ir.all_classes():
        if cls.name in ("Application", "FreeCAD"):
            app_cls = cls
            break
    if app_cls:
        lines.append("")
        lines.append("# From stubs:")
        for prop_name, prop in sorted(app_cls.properties.items()):
            if prop.type:
                lines.append(f"  .{prop_name} -> {prop.type}")

    lines.append("")
    return "\n".join(lines)


def render_gotchas(ir: IR) -> str:
    """Render the [gotchas] section."""
    lines = ["# freecad-gotchas.lap", "", "[gotchas]"]
    for gotcha in ir.gotchas:
        if not gotcha.startswith("- "):
            gotcha = f"- {gotcha}"
        lines.append(gotcha)
    lines.append("")
    return "\n".join(lines)


def render_meta() -> str:
    """Render the [meta] section."""
    return """[meta]
api: FreeCAD
lang: python
modules: FreeCAD, FreeCADGui, Part, PartDesign, Sketcher, Mesh, TechDraw, Path, Fem
import: import FreeCAD as App; import Part; import PartDesign; import Sketcher
"""


def render_remaining(ir: IR, all_domain_patterns: dict[str, list[str]]) -> str:
    """Render all classes/enums that don't match any domain pattern into freecad-misc.lap."""
    all_patterns = []
    for patterns in all_domain_patterns.values():
        all_patterns.extend(patterns)

    unmatched_enums = [e for e in ir.all_enums() if not _matches_any(e.name, all_patterns)]
    unmatched_classes = [c for c in ir.all_classes() if not _matches_any(c.name, all_patterns)]

    lines = ["# freecad-misc.lap", ""]

    if unmatched_enums:
        lines.append("[types]")
        for enum in sorted(unmatched_enums, key=lambda e: e.name):
            lines.append(f"{enum.name}: {' | '.join(enum.values)}")
        lines.append("")

    if unmatched_classes:
        lines.append("[classes]")
        for cls in sorted(unmatched_classes, key=lambda c: c.name):
            lines.extend(_render_class(cls))
            lines.append("")

    return "\n".join(lines)


def _render_class(cls: ClassDef) -> list[str]:
    """Render a single class definition."""
    lines = []

    if cls.is_collection and cls.collection_item_type:
        header = f"{cls.name} *collection<{cls.collection_item_type}>"
    elif cls.parent:
        header = f"{cls.name} : {cls.parent}"
    else:
        header = cls.name
    lines.append(header)

    if cls.description and len(cls.description) < 100:
        lines.append(f"  # {cls.description}")

    for prop_name in sorted(cls.properties):
        prop = cls.properties[prop_name]
        type_str = f": {prop.type}" if prop.type else ""
        lines.append(f"  {prop_name}{type_str}")

    for method_name in sorted(cls.methods):
        method = cls.methods[method_name]
        if method_name == "item" and cls.is_collection:
            continue
        args_str = ", ".join(f"{name}: {typ}" for name, typ in method.args)
        returns_str = f" -> {method.returns}" if method.returns else ""
        static_prefix = "@static " if method.static else ""
        lines.append(f"  {static_prefix}{method_name}({args_str}){returns_str}")

    return lines


def _matches_any(name: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(name, p) for p in patterns)
