# FreeCAD LAP SDK

Compressed, LLM-optimized API reference for FreeCAD.

**~100K+ tokens** covering the FreeCAD Python API in a format any LLM can use.

## Use with any LLM

Paste this into any LLM prompt (ChatGPT, Claude, Gemini, etc.):

```
Read https://halletj.github.io/freecad-lap-sdk/lap/freecad-base.lap for the FreeCAD API reference.
For additional API domains see https://halletj.github.io/freecad-lap-sdk/CLAUDE.md
Help me write a FreeCAD script that [your task here].
```

## Use with Claude Code

Clone this repo. The `CLAUDE.md` file tells Claude Code where to find the API reference automatically.

```bash
git clone https://github.com/halletj/freecad-lap-sdk.git
cd freecad-lap-sdk
# Claude Code reads CLAUDE.md and knows how to use the .lap files
```

## LAP Files

Pre-built `.lap` files are in the `lap/` directory:

| File | Contents |
|---|---|
| [freecad-base.lap](lap/freecad-base.lap) | **Start here.** Navigation graph + gotchas + core types |
| [freecad-part.lap](lap/freecad-part.lap) | Part shapes, primitives, booleans, OCCT |
| [freecad-partdesign.lap](lap/freecad-partdesign.lap) | Body, Pad, Pocket, Revolution, Fillet, etc. |
| [freecad-sketcher.lap](lap/freecad-sketcher.lap) | SketchObject, geometry, constraints |
| [freecad-draft.lap](lap/freecad-draft.lap) | Draft 2D drawing |
| [freecad-techdraw.lap](lap/freecad-techdraw.lap) | Drawing views, dimensions, annotations |
| [freecad-path.lap](lap/freecad-path.lap) | CAM toolpaths, operations |
| [freecad-mesh.lap](lap/freecad-mesh.lap) | Mesh operations |
| [freecad-fem.lap](lap/freecad-fem.lap) | Finite element analysis |
| [freecad-assembly.lap](lap/freecad-assembly.lap) | Assembly constraints |
| [freecad-gui.lap](lap/freecad-gui.lap) | ViewProviders, Selection, Commands |

## Regenerating

If you have FreeCAD stubs available, you can regenerate the `.lap` files:

```bash
pip install -e .
python -m freecad_lap
```

The tool automatically:
1. Finds FreeCAD API stubs (from `freecad-stubs` PyPI package or local install)
2. Optionally clones [FreeCAD-documentation](https://github.com/FreeCAD/FreeCAD-documentation) for descriptions
3. Merges stubs (types/signatures) + wiki docs (descriptions)
4. Renders partitioned `.lap` files to `lap/`

## What is LAP?

LAP is a compressed API reference format inspired by [LAPIS](https://arxiv.org/abs/2602.18541), extended for object-oriented desktop SDKs. It uses compact syntax — class inheritance with `:`, properties without parens, methods with parens, `*collection<T>` shorthand — to fit large API surfaces into LLM context windows.

See [docs/freecad-research.md](docs/freecad-research.md) for the full research.

## Project Structure

```
lap/                Generated .lap files (checked in, ready to use)
freecad_lap/        Python converter package
  __main__.py       Entry point: python -m freecad_lap
  ir.py             Intermediate representation
  discover.py       Auto-find FreeCAD stubs
  stubs.py          Parse .py/.pyi stubs into IR
  scraper.py        Parse FreeCAD wiki docs
  enrich.py         Merge stubs + wiki descriptions
  render.py         IR -> .lap format
  build.py          Full build pipeline
  mcp_server.py     MCP tool functions
domains.yaml        Class-to-domain mapping
tests/              Test suite
docs/               Research and design docs
```
