"""Parse FreeCAD documentation from a local clone of FreeCAD-documentation."""

import logging
import re
import subprocess
from pathlib import Path

from .ir import ClassDef, MethodDef, PropertyDef

logger = logging.getLogger(__name__)

_REPO_URL = "https://github.com/FreeCAD/FreeCAD-documentation.git"
_CLONE_DIR = Path.home() / ".cache" / "freecad-lap" / "FreeCAD-documentation"
_WIKI_SUBDIR = Path("wiki")


def find_or_clone_docs() -> Path | None:
    """Find local FreeCAD-documentation repo, cloning if needed."""
    candidates = [
        _CLONE_DIR / _WIKI_SUBDIR,
        Path("/tmp/FreeCAD-documentation") / _WIKI_SUBDIR,
        Path.home() / "git" / "FreeCAD-documentation" / _WIKI_SUBDIR,
    ]
    for candidate in candidates:
        if candidate.is_dir() and any(candidate.glob("*.md")):
            return candidate

    # Not found -- clone it (sparse, wiki/ only)
    logger.info(f"Cloning {_REPO_URL} to {_CLONE_DIR}...")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--filter=blob:none",
             "--sparse", _REPO_URL, str(_CLONE_DIR)],
            check=True, capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "-C", str(_CLONE_DIR), "sparse-checkout", "set", "wiki"],
            check=True, capture_output=True, text=True,
        )
        docs_dir = _CLONE_DIR / _WIKI_SUBDIR
        if docs_dir.is_dir():
            return docs_dir
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.warning(f"Failed to clone FreeCAD-documentation: {e}")

    return None


def parse_api_page(class_name: str, markdown: str) -> ClassDef | None:
    """Parse a FreeCAD wiki Markdown page for API information."""
    description = ""
    methods = {}
    properties = {}

    lines = markdown.splitlines()

    # Extract description from the first paragraph after the title
    in_description = False
    desc_parts = []
    for line in lines:
        if line.startswith("# "):
            in_description = True
            continue
        if in_description:
            if line.startswith("#") or line.startswith("```"):
                break
            stripped = line.strip()
            if stripped:
                desc_parts.append(stripped)
            elif desc_parts:
                break
    description = " ".join(desc_parts)

    # Look for method/property sections
    current_section = ""
    for line in lines:
        if re.match(r"^##\s+", line):
            section_text = line.lstrip("#").strip().lower()
            if "method" in section_text:
                current_section = "methods"
            elif "propert" in section_text:
                current_section = "properties"
            elif "attribute" in section_text:
                current_section = "properties"
            else:
                current_section = ""
        elif current_section and line.startswith("* ") or line.startswith("- "):
            # List items in method/property sections
            item = line.lstrip("*- ").strip()
            # Parse patterns like: `methodName(args)` -- description
            # or: `propertyName` -- description
            match = re.match(r"`?(\w+)\(([^)]*)\)`?\s*[-:—]\s*(.*)", item)
            if match and current_section == "methods":
                name = match.group(1)
                desc = match.group(3).strip()
                methods[name] = MethodDef(name=name, description=desc)
            else:
                match = re.match(r"`?(\w+)`?\s*[-:—]\s*(.*)", item)
                if match and current_section == "properties":
                    name = match.group(1)
                    desc = match.group(2).strip()
                    properties[name] = PropertyDef(name=name, description=desc)

    if not description and not methods and not properties:
        return None

    return ClassDef(
        name=class_name, description=description,
        methods=methods, properties=properties,
    )


def scrape_local_docs(docs_dir: Path | None = None) -> dict[str, ClassDef]:
    """Parse FreeCAD wiki docs for API class information."""
    if docs_dir is None:
        docs_dir = find_or_clone_docs()
    if docs_dir is None:
        return {}

    logger.info(f"Reading wiki docs from {docs_dir}")

    # FreeCAD wiki has pages like "PartDesign_Pad.md", "Part_Box.md", etc.
    # Also "FreeCAD_API.md", "Part_API.md", etc.
    scraped = {}

    # Parse API pages
    api_pages = sorted(docs_dir.glob("*_API.md"))
    for api_page in api_pages:
        try:
            markdown = api_page.read_text(encoding="utf-8")
            _parse_api_list_page(api_page.stem, markdown, scraped)
        except Exception as e:
            logger.debug(f"Failed to parse {api_page.name}: {e}")

    # Parse feature/class pages
    class_pages = sorted(docs_dir.glob("*.md"))
    for page in class_pages:
        stem = page.stem
        # Skip non-class pages
        if stem.startswith("_") or stem.lower().startswith("category"):
            continue
        # Extract class name from page name (e.g., "Part_Box" -> "Box")
        class_name = _page_stem_to_class(stem)
        if not class_name:
            continue
        try:
            markdown = page.read_text(encoding="utf-8")
            cls = parse_api_page(class_name, markdown)
            if cls and class_name not in scraped:
                scraped[class_name] = cls
        except Exception as e:
            logger.debug(f"Failed to parse {page.name}: {e}")

    logger.info(f"Parsed {len(scraped)} class entries from wiki docs")
    return scraped


def _parse_api_list_page(stem: str, markdown: str, result: dict):
    """Parse an API list page (like Part_API.md) for class/method listings."""
    # These pages typically list available functions and properties
    # They're less structured than individual class pages
    pass


def _page_stem_to_class(stem: str) -> str:
    """Convert wiki page stem to likely class name.

    Examples:
        Part_Box -> Box
        PartDesign_Pad -> Pad
        Sketcher_SketchObject -> SketchObject
    """
    # Known module prefixes in wiki page names
    prefixes = [
        "PartDesign_", "Part_", "Sketcher_", "TechDraw_", "Path_",
        "Mesh_", "Fem_", "Draft_", "Assembly_", "Arch_", "FreeCAD_",
        "Std_", "OpenSCAD_",
    ]
    for prefix in prefixes:
        if stem.startswith(prefix):
            return stem[len(prefix):]
    return ""
