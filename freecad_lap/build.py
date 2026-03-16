"""Full build pipeline: discover stubs, scrape, enrich, render, bundle."""

import logging
from pathlib import Path

import yaml

from .discover import find_stubs
from .enrich import enrich_ir
from .ir import IR
from .patches import apply_patches
from .render import (
    render_domain, render_draft_functions, render_gotchas, render_graph,
    render_meta, render_part_functions, render_remaining,
)
from .scraper import scrape_local_docs
from .stubs import parse_stubs

logger = logging.getLogger(__name__)

DEFAULT_GOTCHAS = [
    "ALWAYS call doc.recompute() after modifying objects -- nothing updates without it",
    "Units are millimeters internally, not centimeters (unlike Fusion 360)",
    "Create objects via doc.addObject('TypeString', 'Name') -- type string must be exact",
    "Features must be added to a Body via body.newObject(), not doc.addObject()",
    "Sketch geometry uses Part module types: Part.LineSegment, Part.Circle, etc.",
    "Constraints reference geometry by 0-based index, which can break if geometry order changes",
    "FreeCADGui (Gui) module is unavailable in headless mode (FreeCADCmd)",
    "Use 'import FreeCAD as App' -- the App alias isn't always available outside FreeCAD console",
    "Sketch must have AttachmentSupport (plane) and MapMode set before adding geometry",
    "Topological naming: avoid referencing faces/edges by index in parametric models",
    "Store object references in variables before switching workbenches -- selection clears",
    "Point3D coordinates are in mm: App.Vector(10, 0, 0) means 10mm",
]

# Resolve paths relative to the repo root (parent of freecad_lap/)
_REPO_ROOT = Path(__file__).parent.parent
_DEFAULT_OUTPUT = _REPO_ROOT / "lap"
_DEFAULT_DOMAINS = _REPO_ROOT / "domains.yaml"
_DEFAULT_PATCHES = _REPO_ROOT / "patches.yaml"


def build_lap_files(
    output_dir: str | Path = _DEFAULT_OUTPUT,
    stubs_path: str | None = None,
    domains_yaml: str | Path = _DEFAULT_DOMAINS,
    patches_yaml: str | Path = _DEFAULT_PATCHES,
):
    """Run the full build pipeline. Finds stubs, scrapes docs, enriches, renders."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Stage 1: Get stubs
    if stubs_path:
        logger.info(f"Using provided stubs path: {stubs_path}")
        ir = parse_stubs(stubs_path)
    else:
        source = find_stubs()
        if source:
            ir = parse_stubs(source.path)
        else:
            logger.warning("No stubs found. Building from docs only.")
            ir = IR()

    # Stage 2: Enrich from wiki docs
    scraped = scrape_local_docs()
    if scraped:
        enrich_ir(ir, scraped)
    else:
        logger.warning("No wiki docs found. Proceeding with stubs only.")

    # Stage 2.5: Apply manual patches
    apply_patches(ir, patches_yaml)

    # Add default gotchas
    ir.gotchas = DEFAULT_GOTCHAS + ir.gotchas

    # Stage 3: Classify & render
    domains = _load_domains(domains_yaml)

    for domain_name, patterns in domains.items():
        content = render_domain(ir, domain_name, patterns)
        filepath = out / f"freecad-{domain_name}.lap"
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Wrote {filepath}")

    # Append module-level functions to domain files
    _append_to_domain(out, "part", render_part_functions())
    _append_to_domain(out, "draft", render_draft_functions())

    # Render misc (everything that didn't match any domain)
    misc_content = render_remaining(ir, domains)
    (out / "freecad-misc.lap").write_text(misc_content, encoding="utf-8")
    logger.info(f"Wrote {out / 'freecad-misc.lap'}")

    # Render always-load files
    graph_content = render_graph(ir)
    (out / "freecad-graph.lap").write_text(graph_content, encoding="utf-8")

    gotchas_content = render_gotchas(ir)
    (out / "freecad-gotchas.lap").write_text(gotchas_content, encoding="utf-8")

    meta_content = render_meta()
    core_file = out / "freecad-core.lap"
    if core_file.exists():
        existing = core_file.read_text(encoding="utf-8")
        core_file.write_text(meta_content + "\n" + existing, encoding="utf-8")

    # Stage 4: Bundle
    base_parts = []
    for name in ["freecad-graph.lap", "freecad-gotchas.lap", "freecad-core.lap"]:
        part_file = out / name
        if part_file.exists():
            base_parts.append(part_file.read_text(encoding="utf-8"))
    base_content = "\n".join(base_parts)
    (out / "freecad-base.lap").write_text(base_content, encoding="utf-8")
    logger.info(f"Wrote {out / 'freecad-base.lap'}")

    _print_summary(out)


def _append_to_domain(out: Path, domain_name: str, content: str):
    """Append extra content to a domain .lap file."""
    filepath = out / f"freecad-{domain_name}.lap"
    if filepath.exists():
        existing = filepath.read_text(encoding="utf-8")
        filepath.write_text(existing + "\n" + content, encoding="utf-8")
    else:
        filepath.write_text(f"# freecad-{domain_name}.lap\n\n{content}", encoding="utf-8")


def _load_domains(domains_yaml: str | Path) -> dict[str, list[str]]:
    path = Path(domains_yaml)
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f)
    else:
        logger.warning(f"{domains_yaml} not found, using default domains")
        return {
            "core": ["Application", "Document", "Document*", "Vector", "Vector*",
                      "Matrix*", "Placement*", "Rotation*", "Base", "PropertyContainer"],
            "part": ["Shape", "Shape*", "TopoShape*", "Wire*", "Face*", "Edge*",
                      "Vertex*", "Shell*", "Solid*", "Box", "Cylinder*", "Sphere*"],
            "partdesign": ["Body", "Pad*", "Pocket*", "Revolution*", "Fillet*", "Chamfer*"],
            "sketcher": ["Sketch*", "*Constraint", "Profile*"],
            "mesh": ["Mesh*"],
            "fem": ["Fem*", "FEM*"],
            "gui": ["ViewProvider*", "Selection*", "Command*", "Workbench*"],
        }


def _print_summary(out: Path):
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
    except ImportError:
        logger.info("Install tiktoken for token count summary")
        enc = None

    total_tokens = 0
    print("\n--- Build Summary ---")
    print(f"{'File':<30} {'Size':>8} {'Tokens':>8}")
    print("-" * 50)
    for lap_file in sorted(out.glob("*.lap")):
        content = lap_file.read_text(encoding="utf-8")
        size = len(content)
        tokens = len(enc.encode(content)) if enc else 0
        total_tokens += tokens
        token_str = str(tokens) if enc else "n/a"
        print(f"{lap_file.name:<30} {size:>7}B {token_str:>8}")
    if enc:
        print("-" * 50)
        print(f"{'Total':<30} {'':>8} {total_tokens:>8}")
    print()
