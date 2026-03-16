"""MCP server exposing FreeCAD LAP files as tools."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_LAP_DIR = Path(__file__).parent.parent / "lap"


def lookup_domain(domain: str, lap_dir: str | None = None) -> str:
    """Return the full content of a domain .lap file."""
    d = Path(lap_dir) if lap_dir else DEFAULT_LAP_DIR
    filepath = d / f"freecad-{domain}.lap"
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")
    return f"Domain '{domain}' not found. Available: {', '.join(_list_domains(d))}"


def search_lap(query: str, lap_dir: str | None = None) -> str:
    """Search across all .lap files for a query string."""
    d = Path(lap_dir) if lap_dir else DEFAULT_LAP_DIR
    results = []
    for lap_file in sorted(d.glob("freecad-*.lap")):
        content = lap_file.read_text(encoding="utf-8")
        matching_lines = []
        for i, line in enumerate(content.splitlines(), 1):
            if query.lower() in line.lower():
                matching_lines.append(f"  L{i}: {line.strip()}")
        if matching_lines:
            results.append(f"--- {lap_file.name} ---")
            results.extend(matching_lines[:10])
    return "\n".join(results) if results else f"No matches for '{query}'"


def get_graph(lap_dir: str | None = None) -> str:
    """Return the navigation graph."""
    d = Path(lap_dir) if lap_dir else DEFAULT_LAP_DIR
    filepath = d / "freecad-graph.lap"
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")
    return "freecad-graph.lap not found."


def _list_domains(d: Path) -> list[str]:
    domains = []
    for f in sorted(d.glob("freecad-*.lap")):
        name = f.stem.replace("freecad-", "")
        if name not in ("base", "graph", "gotchas"):
            domains.append(name)
    return domains
