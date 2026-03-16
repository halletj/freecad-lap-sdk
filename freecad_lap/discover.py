"""Auto-discover FreeCAD API type stubs from multiple sources."""

import importlib.util
import logging
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from glob import glob
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class StubSource:
    path: str
    kind: str  # "pip_stubs", "freecad_install", "freecad_env"


# Modules to look for in the stubs package
FREECAD_MODULES = [
    "FreeCAD",
    "FreeCADGui",
    "Part",
    "PartDesign",
    "Sketcher",
    "Mesh",
    "Path",
    "TechDraw",
    "Draft",
    "Fem",
    "Points",
    "Robot",
    "Spreadsheet",
    "Surface",
    "Import",
    "MeshPart",
    "ReverseEngineering",
    "Assembly",
]


def find_stubs() -> StubSource | None:
    """Try multiple sources to find FreeCAD API stubs. Returns first success or None."""
    finders = [
        _try_freecad_env,
        _try_pip_freecad_stubs,
        _try_freecad_install,
    ]
    for finder in finders:
        try:
            result = finder()
            if result:
                logger.info(f"Found stubs: {result.kind} at {result.path}")
                return result
        except Exception as e:
            logger.debug(f"{finder.__name__} failed: {e}")
    logger.warning("No stub source found. Will rely on doc scraping alone.")
    return None


def _try_freecad_env() -> StubSource | None:
    """Check FREECAD_STUBS_PATH environment variable."""
    stubs_path = os.environ.get("FREECAD_STUBS_PATH")
    if not stubs_path:
        return None
    path = Path(stubs_path)
    if path.is_dir() and _has_stubs(path):
        return StubSource(path=str(path), kind="freecad_env")
    return None


def _try_pip_freecad_stubs() -> StubSource | None:
    """Find freecad-stubs installed via pip (PEP 561 layout: Module-stubs/)."""
    import site
    search_dirs = []
    try:
        search_dirs.extend(site.getsitepackages())
    except AttributeError:
        pass
    try:
        search_dirs.append(site.getusersitepackages())
    except AttributeError:
        pass
    # Also check sys.path for venv site-packages
    for p in sys.path:
        if "site-packages" in p and p not in search_dirs:
            search_dirs.append(p)

    for sp in search_dirs:
        p = Path(sp)
        if not p.is_dir():
            continue
        # PEP 561 layout: FreeCAD-stubs/__init__.pyi
        stubs_dir = p / "FreeCAD-stubs"
        if stubs_dir.is_dir() and (stubs_dir / "__init__.pyi").exists():
            return StubSource(path=str(p), kind="pip_stubs")
        # Flat layout: FreeCAD.pyi directly in site-packages
        if (p / "FreeCAD.pyi").exists():
            return StubSource(path=str(p), kind="pip_stubs")

    return None


def _try_freecad_install() -> StubSource | None:
    """Find stubs from a local FreeCAD installation."""
    system = platform.system()
    home = Path.home()
    if system == "Darwin":
        patterns = [
            "/Applications/FreeCAD.app/Contents/Resources/lib/python*/",
            str(home / "Applications/FreeCAD.app/Contents/Resources/lib/python*/"),
        ]
    elif system == "Windows":
        local = os.environ.get("LOCALAPPDATA", str(home / "AppData/Local"))
        patterns = [
            f"{local}/FreeCAD/*/bin/",
            "C:/Program Files/FreeCAD/*/bin/",
            "C:/Program Files/FreeCAD/*/lib/",
        ]
    elif system == "Linux":
        patterns = [
            "/usr/lib/freecad/lib/",
            "/usr/lib/freecad-python3/lib/",
            "/usr/share/freecad/lib/",
            str(home / ".local/lib/freecad/lib/"),
            "/snap/freecad/current/usr/lib/freecad/lib/",
        ]
    else:
        return None

    all_matches = []
    for pattern in patterns:
        all_matches.extend(glob(pattern))
    for match in all_matches:
        p = Path(match)
        if _has_stubs(p):
            return StubSource(path=str(p), kind="freecad_install")

    return None


def _has_stubs(path: Path) -> bool:
    """Check if a directory contains FreeCAD stubs."""
    return any(
        (path / f).exists()
        for f in ("FreeCAD.pyi", "FreeCAD.py", "Part.pyi", "Part.py",
                   "FreeCAD/__init__.pyi", "FreeCAD/__init__.py")
    )
