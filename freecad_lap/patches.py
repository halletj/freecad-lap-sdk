"""Apply manual corrections from patches.yaml to the IR before rendering."""

import logging
from pathlib import Path

import yaml

from .ir import IR, ClassDef, MethodDef, PropertyDef

logger = logging.getLogger(__name__)


def apply_patches(ir: IR, patches_yaml: str | Path):
    """Load patches.yaml and apply all corrections to the IR."""
    path = Path(patches_yaml)
    if not path.exists():
        logger.debug(f"No patches file at {path}")
        return

    with open(path) as f:
        patches = yaml.safe_load(f)

    if not patches:
        return

    # Gotchas
    for gotcha in patches.get("gotchas", []):
        if gotcha not in ir.gotchas:
            ir.gotchas.append(gotcha)
            logger.info(f"Added gotcha: {gotcha}")

    # Class patches
    for class_name, ops in patches.get("classes", {}).items():
        cls = _find_class(ir, class_name)
        if cls is None:
            cls = ClassDef(name=class_name, namespace="FreeCAD")
            ir.add_class(cls)
            logger.info(f"Created new class from patch: {class_name}")
        _apply_class_patch(cls, ops)


def _find_class(ir: IR, name: str) -> ClassDef | None:
    """Find a class by name across all namespaces."""
    for ns_classes in ir.namespaces.values():
        if name in ns_classes:
            return ns_classes[name]
    return None


def _apply_class_patch(cls: ClassDef, ops: dict):
    """Apply patch operations to a single class."""
    if "description" in ops:
        cls.description = ops["description"]
        logger.info(f"Patched {cls.name} description")

    for method_name in ops.get("remove_methods", []):
        if method_name in cls.methods:
            del cls.methods[method_name]
            logger.info(f"Removed {cls.name}.{method_name}()")

    for method_name, spec in ops.get("add_methods", {}).items():
        args = [(a[0], a[1]) for a in spec.get("args", [])]
        cls.methods[method_name] = MethodDef(
            name=method_name,
            args=args,
            returns=spec.get("returns", ""),
            static=spec.get("static", False),
            description=spec.get("description", ""),
        )
        logger.info(f"Added {cls.name}.{method_name}()")

    for prop_name in ops.get("remove_properties", []):
        if prop_name in cls.properties:
            del cls.properties[prop_name]
            logger.info(f"Removed {cls.name}.{prop_name}")

    for prop_name, spec in ops.get("add_properties", {}).items():
        cls.properties[prop_name] = PropertyDef(
            name=prop_name,
            type=spec.get("type", ""),
            read_only=spec.get("read_only", True),
            description=spec.get("description", ""),
        )
        logger.info(f"Added {cls.name}.{prop_name}")
