"""Parse FreeCAD Python .pyi stub files into the intermediate representation."""

import ast
import logging
from pathlib import Path

from .ir import IR, ClassDef, MethodDef, PropertyDef, EnumDef

logger = logging.getLogger(__name__)

# Map stub file stems to namespace names
NAMESPACE_MAP = {
    "FreeCAD": "FreeCAD",
    "FreeCADGui": "FreeCADGui",
    "Part": "Part",
    "PartDesign": "PartDesign",
    "Sketcher": "Sketcher",
    "Mesh": "Mesh",
    "MeshPart": "MeshPart",
    "Path": "Path",
    "TechDraw": "TechDraw",
    "Draft": "Draft",
    "Fem": "Fem",
    "FemGui": "FemGui",
    "Points": "Points",
    "Robot": "Robot",
    "Spreadsheet": "Spreadsheet",
    "Surface": "Surface",
    "Import": "Import",
    "ReverseEngineering": "ReverseEngineering",
    "Assembly": "Assembly",
    "Arch": "Arch",
    "BOPTools": "BOPTools",
    "BasicShapes": "BasicShapes",
    "Drawing": "Drawing",
    "Image": "Image",
    "Inspection": "Inspection",
    "Material": "Material",
    "OpenSCAD": "OpenSCAD",
    "Raytracing": "Raytracing",
    "Start": "Start",
    "Test": "Test",
    "Web": "Web",
}

# Infrastructure classes to skip
SKIP_CLASSES = {
    "type",
    "object",
}

# Methods to skip
SKIP_METHODS = {
    "__init__",
    "__repr__",
    "__str__",
    "__eq__",
    "__ne__",
    "__hash__",
    "__del__",
    "__new__",
    "__reduce__",
    "__getstate__",
    "__setstate__",
}


def parse_stubs(stubs_path: str) -> IR:
    """Parse all .pyi and .py stub files under stubs_path into an IR."""
    ir = IR()
    stubs_dir = Path(stubs_path)

    # Collect files to parse: prefer .pyi over .py if both exist
    files_to_parse = {}  # stem -> path

    # Check for top-level .pyi files (e.g., FreeCAD.pyi, Part.pyi)
    for pyi_file in sorted(stubs_dir.glob("*.pyi")):
        stem = pyi_file.stem
        if stem.startswith("_"):
            continue
        if stem in NAMESPACE_MAP:
            files_to_parse[stem] = pyi_file

    # Check for .py files as fallback
    for py_file in sorted(stubs_dir.glob("*.py")):
        stem = py_file.stem
        if stem.startswith("_") or stem == "setup":
            continue
        if stem in NAMESPACE_MAP and stem not in files_to_parse:
            files_to_parse[stem] = py_file

    # Check for package-style stubs (e.g., FreeCAD/__init__.pyi)
    for subdir in sorted(stubs_dir.iterdir()):
        if not subdir.is_dir():
            continue
        # Handle PEP 561 *-stubs directories (e.g., FreeCAD-stubs/)
        dir_name = subdir.name
        if dir_name.endswith("-stubs"):
            module_name = dir_name[:-6]  # Strip "-stubs" suffix
        elif dir_name.startswith("_"):
            continue
        else:
            module_name = dir_name
        if module_name not in NAMESPACE_MAP:
            continue
        # Already have a top-level file? Skip.
        if module_name in files_to_parse:
            continue
        init_pyi = subdir / "__init__.pyi"
        init_py = subdir / "__init__.py"
        if init_pyi.exists():
            files_to_parse[module_name] = init_pyi
        elif init_py.exists():
            files_to_parse[module_name] = init_py

    for stem, path in sorted(files_to_parse.items()):
        namespace = NAMESPACE_MAP.get(stem, stem)
        logger.info(f"Parsing {path.name} as {namespace}")
        _parse_file(path, namespace, ir)

    return ir


def _parse_file(path: Path, namespace: str, ir: IR):
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        logger.warning(f"Failed to parse {path}: {e}")
        return

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            if node.name in SKIP_CLASSES:
                continue
            if _is_enum_class(node):
                ir.add_enum(_parse_enum(node, namespace))
            else:
                ir.add_class(_parse_class(node, namespace))


def _is_enum_class(node: ast.ClassDef) -> bool:
    """Detect enum-like classes: have value assignments but no methods."""
    has_assignments = False
    has_methods = False
    for item in node.body:
        if isinstance(item, (ast.Assign, ast.AnnAssign)):
            has_assignments = True
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            has_methods = True
    return has_assignments and not has_methods


def _parse_enum(node: ast.ClassDef, namespace: str) -> EnumDef:
    values = []
    description = _extract_docstring(node)
    for item in node.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    values.append(target.id)
        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            if not item.target.id.startswith("_"):
                values.append(item.target.id)
    return EnumDef(name=node.name, namespace=namespace, values=values,
                   description=description)


def _parse_class(node: ast.ClassDef, namespace: str) -> ClassDef:
    parent = _extract_parent(node)
    description = _extract_docstring(node)
    properties = {}
    methods = {}
    is_collection = False

    for item in node.body:
        if isinstance(item, ast.FunctionDef):
            if _is_property(item):
                prop = _parse_property(item)
                if prop:
                    properties[prop.name] = prop
            elif item.name in SKIP_METHODS:
                continue
            elif item.name.startswith("_"):
                continue
            else:
                method = _parse_method(item)
                if method:
                    methods[method.name] = method
                    if method.name == "item" and method.returns:
                        is_collection = True
        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            # Class-level annotated assignments (common in stubs)
            name = item.target.id
            if not name.startswith("_"):
                prop_type = _annotation_to_str(item.annotation) if item.annotation else ""
                properties[name] = PropertyDef(name=name, type=prop_type)

    cls = ClassDef(
        name=node.name, namespace=namespace, parent=parent,
        description=description,
        properties=properties, methods=methods, is_collection=is_collection,
    )
    if is_collection and "item" in methods:
        cls.collection_item_type = methods["item"].returns
    return cls


def _extract_parent(node: ast.ClassDef) -> str:
    if not node.bases:
        return ""
    base = node.bases[0]
    if isinstance(base, ast.Name):
        name = base.id
        return "" if name == "object" else name
    if isinstance(base, ast.Attribute):
        return base.attr
    return ""


def _extract_docstring(node: ast.ClassDef | ast.FunctionDef) -> str:
    if (node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)):
        return node.body[0].value.value.strip()
    return ""


def _is_property(node: ast.FunctionDef) -> bool:
    return any(
        (isinstance(d, ast.Name) and d.id == "property")
        or (isinstance(d, ast.Attribute) and d.attr in ("getter", "setter"))
        for d in node.decorator_list
    )


def _is_setter(node: ast.FunctionDef) -> bool:
    return any(isinstance(d, ast.Attribute) and d.attr == "setter" for d in node.decorator_list)


def _parse_property(node: ast.FunctionDef) -> PropertyDef | None:
    if _is_setter(node):
        return None
    return_type = _annotation_to_str(node.returns) if node.returns else ""
    return PropertyDef(name=node.name, type=return_type, read_only=True)


def _parse_method(node: ast.FunctionDef) -> MethodDef | None:
    is_static = any(isinstance(d, ast.Name) and d.id == "staticmethod" for d in node.decorator_list)
    is_classmethod = any(isinstance(d, ast.Name) and d.id == "classmethod" for d in node.decorator_list)
    args = []
    for arg in node.args.args:
        if arg.arg in ("self", "cls"):
            continue
        arg_type = _annotation_to_str(arg.annotation) if arg.annotation else ""
        args.append((arg.arg, arg_type))
    return_type = _annotation_to_str(node.returns) if node.returns else ""
    description = _extract_docstring(node)
    return MethodDef(name=node.name, args=args, returns=return_type,
                     static=is_static or is_classmethod, description=description)


def _annotation_to_str(node) -> str:
    if node is None:
        return ""
    if isinstance(node, ast.Constant):
        v = str(node.value)
        # Strip module prefixes for readability
        if "." in v:
            return v.rsplit(".", 1)[-1]
        return v
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        # Keep short: just the final attribute name
        return node.attr
    if isinstance(node, ast.Subscript):
        base = _annotation_to_str(node.value)
        inner = _annotation_to_str(node.slice)
        return f"{base}[{inner}]"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        # Union type: X | Y
        left = _annotation_to_str(node.left)
        right = _annotation_to_str(node.right)
        return f"{left} | {right}"
    if isinstance(node, ast.Tuple):
        parts = [_annotation_to_str(e) for e in node.elts]
        return ", ".join(parts)
    return ""
