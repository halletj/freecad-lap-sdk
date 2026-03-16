"""Enrich stub-derived IR with descriptions from scraped wiki docs."""

import logging

from .ir import IR, ClassDef

logger = logging.getLogger(__name__)


def enrich_ir(ir: IR, scraped: dict[str, ClassDef]):
    """Merge scraped class data into the existing IR."""
    for class_name, scraped_cls in scraped.items():
        found = False
        for ns_classes in ir.namespaces.values():
            if class_name in ns_classes:
                existing = ns_classes[class_name]
                scraped_cls.namespace = existing.namespace
                ir.merge_class(scraped_cls)
                found = True
                break

        if not found:
            if not scraped_cls.namespace:
                scraped_cls.namespace = _guess_namespace(class_name)
            ir.add_class(scraped_cls)
            logger.info(f"Added {class_name} from docs (not in stubs)")


def _guess_namespace(class_name: str) -> str:
    """Guess the FreeCAD namespace for a class based on its name."""
    partdesign_prefixes = (
        "Pad", "Pocket", "Revolution", "Groove", "Fillet", "Chamfer",
        "Draft", "Thickness", "Pipe", "Loft", "Mirrored", "LinearPattern",
        "PolarPattern", "MultiTransform", "Body", "Feature",
    )
    sketcher_prefixes = ("Sketch", "Constraint")
    part_prefixes = (
        "Shape", "TopoShape", "Wire", "Face", "Edge", "Vertex", "Shell",
        "Solid", "Compound", "Box", "Cylinder", "Sphere", "Cone", "Torus",
        "BSpline", "Bezier", "Line", "Circle", "Arc", "Ellipse",
    )
    mesh_prefixes = ("Mesh",)
    fem_prefixes = ("Fem", "FEM")
    techdraw_prefixes = ("TechDraw", "DrawView", "DrawPage")
    path_prefixes = ("Path", "Tool", "Toolbit")
    gui_prefixes = ("ViewProvider", "Selection", "Command", "Workbench")

    for prefix in gui_prefixes:
        if class_name.startswith(prefix):
            return "FreeCADGui"
    for prefix in partdesign_prefixes:
        if class_name.startswith(prefix):
            return "PartDesign"
    for prefix in sketcher_prefixes:
        if class_name.startswith(prefix):
            return "Sketcher"
    for prefix in part_prefixes:
        if class_name.startswith(prefix):
            return "Part"
    for prefix in mesh_prefixes:
        if class_name.startswith(prefix):
            return "Mesh"
    for prefix in fem_prefixes:
        if class_name.startswith(prefix):
            return "Fem"
    for prefix in techdraw_prefixes:
        if class_name.startswith(prefix):
            return "TechDraw"
    for prefix in path_prefixes:
        if class_name.startswith(prefix):
            return "Path"
    return "FreeCAD"
