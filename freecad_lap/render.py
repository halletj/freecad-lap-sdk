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
        name_counts = _count_names(matching_classes)
        for cls in sorted(matching_classes, key=lambda c: (c.name, c.namespace)):
            lines.extend(_render_class(cls, disambiguate=name_counts[cls.name] > 1))
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
    lines.append("  .Placement(pos, rot, center=Vector()) -> Placement  # also: (matrix)")
    lines.append("  .Rotation(axis, angle) -> Rotation  # also: (yaw, pitch, roll), (q0, q1, q2, q3)")
    lines.append("")
    lines.append("Document")
    lines.append("  .Objects -> list[DocumentObject]")
    lines.append("  .addObject(type: str, name: str) -> DocumentObject")
    lines.append("  .removeObject(name: str) -> None")
    lines.append("  .recompute() -> int")
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
    lines.append("  .AttachmentSupport -> PropertyLinkSubList  # the plane (was .Support pre-0.19)")
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


def render_part_functions() -> str:
    """Render Part module-level convenience functions."""
    return """\
[functions]
# Part module convenience functions (import Part)
Part.makeBox(length: float, width: float, height: float, pnt: Vector = Vector(0,0,0), dir: Vector = Vector(0,0,1)) -> Shape
Part.makeCylinder(radius: float, height: float, pnt: Vector = Vector(0,0,0), dir: Vector = Vector(0,0,1), angle: float = 360) -> Shape
Part.makeSphere(radius: float, pnt: Vector = Vector(0,0,0), dir: Vector = Vector(0,0,1), angle1: float = -90, angle2: float = 90, angle3: float = 360) -> Shape
Part.makeCone(radius1: float, radius2: float, height: float, pnt: Vector = Vector(0,0,0), dir: Vector = Vector(0,0,1), angle: float = 360) -> Shape
Part.makeTorus(radius1: float, radius2: float, pnt: Vector = Vector(0,0,0), dir: Vector = Vector(0,0,1), angle1: float = 0, angle2: float = 360, angle: float = 360) -> Shape
Part.makeHelix(pitch: float, height: float, radius: float, angle: float = 0, lefthand: bool = False, heightstyle: bool = False) -> Shape
Part.makeLine(startpnt: Vector | tuple, endpnt: Vector | tuple) -> Shape
Part.makePolygon(pntslist: list[Vector], closed: bool = False) -> Shape  # returns Wire
Part.makeLoft(profiles: list[Shape], solid: bool = False, ruled: bool = False, closed: bool = False, maxDegree: int = 5) -> Shape
Part.makeCompound(shapes: list[Shape]) -> Shape
Part.makeShell(faces: list[Shape]) -> Shape
Part.makeSolid(shell: Shape) -> Shape
Part.show(shape: Shape, name: str = "Shape") -> DocumentObject  # adds to active doc
Part.read(filename: str) -> Shape  # reads BREP/IGES/STEP
Part.export(objects: list[Shape], filename: str) -> None  # format from extension
"""


def render_draft_functions() -> str:
    """Render Draft module-level convenience functions."""
    return """\
[functions]
# Draft module convenience functions (import Draft)
# Modern snake_case names (0.19+); old camelCase names still work but are deprecated

# Creation
Draft.make_line(first_param: Vector | Part.LineSegment, last_param: Vector = None) -> DocumentObject
Draft.make_wire(pointslist: list[Vector] | Part.Wire, closed: bool = False, placement: Placement = None, face: bool = None, support: object = None) -> DocumentObject
Draft.make_circle(radius: float | Part.Edge, placement: Placement = None, face: bool = None, startangle: float = None, endangle: float = None, support: object = None) -> DocumentObject
Draft.make_rectangle(length: float, height: float = 0, placement: Placement = None, face: bool = None, support: object = None) -> DocumentObject
Draft.make_polygon(nfaces: int, radius: float = 1, inscribed: bool = True, placement: Placement = None, face: bool = None, support: object = None) -> DocumentObject
Draft.make_bspline(pointslist: list[Vector], closed: bool = False, placement: Placement = None, face: bool = None, support: object = None) -> DocumentObject
Draft.make_text(string: str | list[str], placement: Placement = None, screen: bool = False) -> DocumentObject
Draft.make_linear_dimension(p1: Vector, p2: Vector, dim_line: Vector = None) -> DocumentObject
Draft.make_angular_dimension(center: Vector = Vector(0,0,0), angles: list[float] = None, dim_line: Vector = None) -> DocumentObject

# Modification
Draft.move(selection: object | list, vector: Vector, copy: bool = False) -> object | list
Draft.rotate(selection: object | list, angle: float, center: Vector = Vector(0,0,0), axis: Vector = Vector(0,0,1), copy: bool = False) -> object | list
Draft.scale(selection: object | list, scale: Vector, center: Vector = Vector(0,0,0), copy: bool = False) -> object | list
Draft.offset(obj: object, delta: Vector, copy: bool = False, bind: bool = False, sym: bool = False, occ: bool = False) -> object

# Arrays (use_link=True creates memory-efficient App::Link arrays)
Draft.make_ortho_array(base_object: object, v_x: Vector = Vector(10,0,0), v_y: Vector = Vector(0,10,0), v_z: Vector = Vector(0,0,10), n_x: int = 2, n_y: int = 2, n_z: int = 1, use_link: bool = True) -> DocumentObject
Draft.make_polar_array(base_object: object, number: int = 5, angle: float = 360, center: Vector = Vector(0,0,0), use_link: bool = True) -> DocumentObject
Draft.make_circular_array(base_object: object, r_distance: float = 100, tan_distance: float = 50, number: int = 3, symmetry: int = 1, center: Vector = Vector(0,0,0), use_link: bool = True) -> DocumentObject
Draft.make_path_array(base_object: object, path_object: object, count: int = 4, use_link: bool = True) -> DocumentObject
"""


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
        name_counts = _count_names(unmatched_classes)
        for cls in sorted(unmatched_classes, key=lambda c: (c.name, c.namespace)):
            lines.extend(_render_class(cls, disambiguate=name_counts[cls.name] > 1))
            lines.append("")

    return "\n".join(lines)


def _render_class(cls: ClassDef, disambiguate: bool = False) -> list[str]:
    """Render a single class definition."""
    lines = []

    display_name = f"{cls.namespace}::{cls.name}" if disambiguate else cls.name
    if cls.is_collection and cls.collection_item_type:
        header = f"{display_name} *collection<{cls.collection_item_type}>"
    elif cls.parent:
        header = f"{display_name} : {cls.parent}"
    else:
        header = display_name
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


def _count_names(classes: list[ClassDef]) -> dict[str, int]:
    """Count how many classes share the same name."""
    counts: dict[str, int] = {}
    for cls in classes:
        counts[cls.name] = counts.get(cls.name, 0) + 1
    return counts


def _matches_any(name: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(name, p) for p in patterns)
