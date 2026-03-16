# Can LAP Be Applied to the FreeCAD API?

Research into adapting LAP (a compressed, LLM-optimized API reference format inspired by
[LAPIS](https://arxiv.org/abs/2602.18541)) to the FreeCAD desktop SDK.

## The FreeCAD API

### Overview

The FreeCAD API is an **object-oriented** SDK for automating FreeCAD through Python scripts,
macros, and workbenches. Like Fusion's API, it is a local, in-process desktop SDK -- but
unlike Fusion, FreeCAD is **open source** (LGPL v2+) and supports true **headless operation**
via `FreeCADCmd`.

### Architecture

- **Top-level modules:** `FreeCAD` (aliased as `App`) for the non-GUI core, `FreeCADGui`
  (aliased as `Gui`) for the GUI layer
- **Geometry kernel:** OpenCASCADE (OCCT), exposed via `Part.Shape` (TopoShape)
- **Workbench modules:** `Part`, `PartDesign`, `Sketcher`, `Draft`, `Arch`/`BIM`,
  `TechDraw`, `Path` (CAM), `Mesh`, `Fem`, `Assembly`, `Spreadsheet`, and more
- **Hierarchy:**
  ```
  FreeCAD (App) -- application singleton
    └── Document (App.ActiveDocument)
          ├── App::Part (spatial container, like Fusion's Component)
          │     ├── PartDesign::Body (single solid, linear feature chain)
          │     │     ├── Sketcher::SketchObject
          │     │     ├── PartDesign::Pad (additive feature)
          │     │     ├── PartDesign::Pocket (subtractive feature)
          │     │     └── ... (ordered chain via BaseFeature)
          │     └── App::Part (nested sub-assembly)
          ├── Part::Feature (standalone BRep shapes)
          ├── Mesh::Feature
          └── ... (any DocumentObject subclass)
  ```
- **Pattern:** Open-ended object model where any `DocumentObject` subclass can live in a
  Document. Less structured than Fusion's strict Component hierarchy, but more flexible.

### Scale of the API

The FreeCAD API is **large and fragmented**:

- **~1,700+ C++ classes** across all namespaces (though ~1,200 are STEP/IFC schema types)
- **~350+ classes** in the App namespace alone (properties, document objects, expressions)
- Dozens of shape classes in `Part` wrapping OpenCASCADE
- ~20-30 feature classes in `PartDesign`
- ~15 classes in `Sketcher`
- Hundreds of `ViewProvider` classes in the Gui namespace
- 15-50+ classes per workbench module (Fem, TechDraw, Path, Mesh, Draft, Arch)
- **C++ workbenches:** Part, PartDesign, Sketcher, Mesh, TechDraw, Spreadsheet, Points,
  ReverseEngineering, Robot, FEM
- **Python workbenches:** Draft, Arch/BIM, Path (CAM), OpenSCAD, Addon Manager

A full API reference likely runs into **hundreds of thousands of tokens**, making it -- like
Fusion -- far too large for any LLM context window.

### Core Class Inheritance

```
Base::BaseClass
  └── Base::Persistence
        └── App::PropertyContainer
              ├── App::Document
              └── App::ExtensionContainer
                    └── App::TransactionalObject
                          └── App::DocumentObject
                                └── App::GeoFeature
                                      ├── App::Part
                                      ├── Part::Feature
                                      │     ├── Part::Primitive (Box, Cylinder, etc.)
                                      │     └── PartDesign::Feature
                                      ├── Mesh::Feature
                                      └── Fem::Constraint
```

### Current Approaches: FreeCAD + LLMs

Three MCP servers address the FreeCAD + LLM challenge:

1. **[neka-nat/freecad-mcp](https://github.com/neka-nat/freecad-mcp)** -- FreeCAD addon
   runs a local RPC server; MCP server connects to it. 9 tools including `execute_code`
   for arbitrary Python execution, plus `create_object`, `edit_object`, `get_view`.
   Has `--only-text-feedback` flag to reduce token costs by skipping screenshots.

2. **[contextform/freecad-mcp](https://github.com/contextform/freecad-mcp)** -- Python
   bridge installed as "AICopilot" workbench. ~45 tools covering PartDesign (13 ops),
   Part (18 ops), View Control (14 ops), plus arbitrary Python execution.

3. **[proximile/FreeCAD-MCP](https://github.com/proximile/FreeCAD-MCP)** -- Docker-based,
   headless FreeCAD via XML-RPC. 57 tools covering document management, Part primitives,
   PartDesign operations, Draft 2D, booleans, transforms, export (STEP/STL/OBJ/IGES),
   viewport screenshots, measurements. Most feature-rich of the three.

All use **on-demand retrieval or direct execution** rather than stuffing the API into
context -- the same pattern as Fusion MCP servers.

## LAP: What It Was Designed For

LAP (inspired by LAPIS) was originally designed for **REST/HTTP APIs** but has been
extended for **object-oriented desktop SDKs** -- specifically the Autodesk Fusion API
(see [fusion-research.md](fusion-research.md)). The Fusion LAP format uses:

- `[meta]` -- API name, version, language, namespaces
- `[types]` -- Enums and value types
- `[classes]` -- Classes with inheritance (`:` syntax), properties, methods
- `[graph]` -- Object graph navigation from the application root
- `[gotchas]` -- Common pitfalls
- `*collection<T>` shorthand for collection classes

The key question is whether this format -- already extended for Fusion's OOP SDK -- can
be applied to FreeCAD's differently-structured Python API.

## Gap Analysis: Fusion API vs FreeCAD API

| Concept | Fusion API | FreeCAD API |
|---|---|---|
| **Namespaces** | 3 (`adsk.core`, `adsk.fusion`, `adsk.cam`) | 2 core + 10+ workbench modules |
| **Module structure** | Clean, unified hierarchy | Fragmented, workbench-centric |
| **Object creation** | `collection.add(input)` pattern | `doc.addObject('TypeString', 'Name')` |
| **Feature creation** | Input object pattern (create → configure → add) | Direct property assignment + recompute |
| **Recompute** | Automatic | Manual (`doc.recompute()` required) |
| **Type stubs** | Official (bundled with install) | Community (`freecad-stubs` on PyPI) |
| **Collections** | Typed collection classes with `.item()`, `.count` | Python lists, `Group` property |
| **Inheritance** | `Base` → `Feature` → `ExtrudeFeature` | `DocumentObject` → `GeoFeature` → `Part::Feature` → ... |
| **Assembly** | Built-in from day 1 (Component/Joint) | New in v1.0 (Assembly workbench) |
| **Timeline** | Per-component, unified | Per-Body feature chain |
| **Geometry kernel** | Proprietary | OpenCASCADE (OCCT) |
| **Headless** | No (requires GUI) | Yes (`FreeCADCmd`) |
| **Open source** | No | Yes (LGPL v2+) |

### Key Differences That Affect LAP Adaptation

1. **String-based type system** -- FreeCAD creates objects via string identifiers like
   `'PartDesign::Body'` or `'Part::Box'`. These type strings are critical API knowledge
   that doesn't exist in Fusion.

2. **No input object pattern** -- Fusion uses `createInput()` → configure → `add()`.
   FreeCAD uses direct property assignment: create object, set properties, then
   `doc.recompute()`.

3. **Flat collections** -- Fusion has typed collection classes (`ExtrudeFeatures`,
   `Sketches`). FreeCAD objects are in flat `Document.Objects` list, filtered by type.
   The `*collection<T>` shorthand is less applicable.

4. **Property system** -- FreeCAD has a rich property type system (`App::PropertyLength`,
   `App::PropertyVector`, `App::PropertyLink`, etc.) that is central to scripting.
   Properties are set via direct assignment (`obj.Length = 10.0`).

5. **Module fragmentation** -- FreeCAD's API is spread across many independent modules
   with different conventions. `Part` uses direct shape construction, `PartDesign` uses
   feature chains, `Draft` uses convenience functions, `Sketcher` uses constraint IDs.

6. **OpenCASCADE exposure** -- FreeCAD exposes OCCT types directly (e.g.
   `Part.Shape.Faces[0].Surface`). This is a large API surface that Fusion abstracts away.

## Feasibility Assessment

### What Transfers Directly from Fusion LAP

- **`[meta]` section** -- API name, version, language, module imports
- **`[classes]` section** -- Class definitions with inheritance work perfectly
- **`[types]` section** -- Enums and type constants
- **`[graph]` section** -- Object graph navigation from `FreeCAD` root
- **`[gotchas]` section** -- FreeCAD has many scripting pitfalls to document
- **Inheritance syntax** (`:`) -- FreeCAD has deep class hierarchies
- **Method/property syntax** -- Properties without parens, methods with parens
- **Token minimality philosophy** -- The core insight applies universally

### What Needs Adaptation

#### 1. Type String Registry

FreeCAD's `addObject()` requires knowing exact type strings. A new section or annotation
is needed:

```
[type-strings]
PartDesign::Body        # single-solid parametric container
PartDesign::Pad         # additive extrusion
PartDesign::Pocket      # subtractive extrusion
PartDesign::Revolution  # additive revolution
Sketcher::SketchObject  # constraint-based 2D sketch
Part::Box               # parametric box primitive
Part::Cylinder          # parametric cylinder primitive
App::Part               # spatial container (assembly)
```

#### 2. Property Type Annotations

FreeCAD's property types matter for scripting:

```
PartDesign::Pad : PartDesign::Feature
  Profile: App::PropertyLink -> Sketcher::SketchObject
  Length: App::PropertyLength = 10.0  # mm
  Type: App::PropertyEnumeration = "Length" | "UpToLast" | "UpToFirst" | "UpToFace" | "TwoLengths"
  Reversed: App::PropertyBool = False
```

#### 3. Workflow Patterns (replaces Input Object pattern)

FreeCAD's create-assign-recompute pattern needs explicit documentation:

```
[patterns]
*create-feature:
  # 1. Create object inside body: body.newObject('Type::String', 'Name')
  # 2. Set properties: obj.Property = value
  # 3. Recompute: doc.recompute()
  # NEVER forget doc.recompute() -- nothing updates without it
```

#### 4. Module-Scoped Classes

FreeCAD classes belong to specific modules more strongly than Fusion classes belong to
namespaces. The domain files should map to workbench modules:

```
freecad-core.lap       # FreeCAD, App.Document, Vector, Placement, properties
freecad-part.lap       # Part module: shapes, primitives, booleans, OCCT wrappers
freecad-partdesign.lap # PartDesign: Body, Pad, Pocket, Revolution, Fillet, etc.
freecad-sketcher.lap   # Sketcher: SketchObject, geometry types, constraints
freecad-draft.lap      # Draft: 2D drawing, convenience functions
freecad-techdraw.lap   # TechDraw: technical drawing views
freecad-path.lap       # Path (CAM): toolpaths, operations
freecad-mesh.lap       # Mesh: polygon mesh operations
freecad-fem.lap        # FEM: finite element analysis
freecad-assembly.lap   # Assembly: constraints, solver
freecad-gui.lap        # FreeCADGui: view providers, selection, commands
```

### Estimated Compression Potential

| Savings Source | Estimated | Notes |
|---|---|---|
| Metadata elimination | ~20% | Remove verbose descriptions, cross-references |
| Signature syntax vs verbose docs | ~30% | One-line methods vs multi-paragraph wiki text |
| Inheritance flattening | ~10% | Show only new members, reference parent |
| Pattern deduplication | ~5% | Less applicable than Fusion (fewer collection classes) |
| Type string registry | +5% | New content needed (Fusion doesn't have this) |
| **Total estimated reduction** | **~55-65%** | Less than Fusion (~60-70%) due to module fragmentation |

For FreeCAD, this could mean reducing from ~400K+ tokens (full docs) to ~140-180K tokens
-- partitioned into ~10 domain files for selective loading.

### Data Sources for Generation

| Source | Content | Availability |
|---|---|---|
| **`freecad-stubs` (PyPI)** | Type info for C++ modules | `pip install freecad-stubs` |
| **FreeCAD Source Docs (Doxygen)** | C++ class hierarchy, ~1,700 classes | https://freecad.github.io/SourceDoc/ |
| **FreeCAD Python API (RTD)** | Part, PartDesign, Sketcher, FEM, Mesh docs | https://freecad-python-api.readthedocs.io/ |
| **FreeCAD Wiki** | Scripting guides, workbench docs, gotchas | https://wiki.freecadweb.org/ |
| **FreeCAD-documentation repo** | Wiki content in Markdown | https://github.com/FreeCAD/FreeCAD-documentation |

The `freecad-stubs` package is the primary source for type information (analogous to
Fusion's bundled `.pyi` stubs). It covers C++ modules but not Python-native workbenches
like Draft and Arch/BIM.

## Recommended Architecture

### Domain Partitioning

| File | Contents | Est. Tokens |
|---|---|---|
| `freecad-graph.lap` | Navigation tree (always-load) | ~2K |
| `freecad-gotchas.lap` | Common pitfalls (always-load) | ~2K |
| `freecad-core.lap` | App, Document, Vector, Placement, Matrix, PropertyContainer, properties | ~8K |
| `freecad-part.lap` | Part.Shape, TopoShape, primitives, booleans, wires, faces, OCCT | ~20K |
| `freecad-partdesign.lap` | Body, Pad, Pocket, Revolution, Fillet, Chamfer, patterns | ~15K |
| `freecad-sketcher.lap` | SketchObject, geometry types, constraints, constraint solver | ~12K |
| `freecad-draft.lap` | Draft module convenience functions, 2D operations | ~8K |
| `freecad-techdraw.lap` | DrawView, dimensions, annotations, templates | ~8K |
| `freecad-path.lap` | Path (CAM) operations, tools, post-processing | ~10K |
| `freecad-mesh.lap` | Mesh operations, import/export | ~5K |
| `freecad-fem.lap` | FEM constraints, analysis, solvers | ~8K |
| `freecad-assembly.lap` | Assembly constraints, Ondsel solver | ~5K |
| `freecad-gui.lap` | FreeCADGui, ViewProviders, Selection, Commands | ~8K |
| `freecad-misc.lap` | Uncategorized classes, enums | ~5K |
| **`freecad-base.lap`** | **Bundle: graph + gotchas + core** | **~12K** |

**Total: ~116K tokens** for the full API in compressed form -- comparable to the Fusion LAP
SDK's ~114K tokens.

### Converter Differences from Fusion

The converter pipeline would be similar but adapted:

```
Stage 1: Parse Stubs
  - Source: freecad-stubs package from PyPI
  - Parser: Same AST-based approach as Fusion
  - Key difference: module names map differently (Part, PartDesign, Sketcher vs adsk.*)

Stage 2: Enrich from Documentation
  - Source: FreeCAD wiki Markdown + Doxygen HTML (vs Fusion's CloudHelp HTML)
  - Key difference: Multiple doc sources to merge
  - The FreeCAD-documentation GitHub repo provides wiki content in Markdown

Stage 3: Classify & Render
  - Domain mapping via domains.yaml (same approach)
  - Key difference: More domains (10+ vs 8) due to workbench fragmentation

Stage 4: Bundle
  - Same approach: graph + gotchas + core -> base
```

### Example LAP Output

```
[meta]
api: FreeCAD
lang: python
modules: FreeCAD, FreeCADGui, Part, PartDesign, Sketcher
import: import FreeCAD as App; import Part; import PartDesign; import Sketcher

[graph]
FreeCAD (App)
  .ActiveDocument -> Document
    .Objects -> list[DocumentObject]
    .addObject(type: str, name: str) -> DocumentObject
    .recompute() -> None
    .getObject(name: str) -> DocumentObject
  .newDocument(name: str) -> Document
  .openDocument(path: str) -> Document
  .Console -> Console
  .Vector(x, y, z) -> Vector
  .Placement(pos, rot) -> Placement

[gotchas]
- ALWAYS call doc.recompute() after modifying objects -- nothing updates without it
- Units are millimeters internally (not centimeters like Fusion)
- Object creation requires exact type strings: doc.addObject('PartDesign::Body', 'Body')
- Features must be added to a Body via body.newObject(), not doc.addObject()
- Sketch geometry uses Part module types: Part.LineSegment, Part.Circle, etc.
- Constraints reference geometry by index (0-based), which can break if geometry order changes
- FreeCADGui (Gui) module is unavailable in headless mode (FreeCADCmd)
- The App/Gui aliases work in FreeCAD console but not guaranteed in external scripts
- Store object references in variables before switching workbenches -- selection clears
- Topological naming: avoid referencing faces/edges by index in parametric models (v1.0 fixes this)
- Sketch must have Support (plane) and MapMode set before adding geometry

[classes]
Document
  Objects: list[DocumentObject]
  ActiveObject: DocumentObject
  Name: str
  FileName: str
  addObject(type: str, name: str) -> DocumentObject
  removeObject(name: str) -> None
  recompute() -> None
  getObject(name: str) -> DocumentObject
  save() -> None
  saveAs(path: str) -> None

DocumentObject
  Name: str
  Label: str
  TypeId: str
  Document: Document
  InList: list[DocumentObject]
  OutList: list[DocumentObject]
  State: list[str]

GeoFeature : DocumentObject
  Placement: Placement
  Shape: Part.Shape

PartDesign::Body : App::Part
  # type string: 'PartDesign::Body'
  Tip: Feature  # final feature in chain
  BaseFeature: Feature
  Origin: Origin
  Group: list[DocumentObject]
  newObject(type: str, name: str) -> DocumentObject

PartDesign::Pad : PartDesign::Feature
  # type string: 'PartDesign::Pad'
  Profile: Sketcher::SketchObject  # App::PropertyLink
  Length: float  # mm, App::PropertyLength
  Type: "Length" | "UpToLast" | "UpToFirst" | "UpToFace" | "TwoLengths"
  Reversed: bool
  Symmetric: bool
  Midplane: bool

Sketcher::SketchObject : Part::Part2DObject
  # type string: 'Sketcher::SketchObject'
  GeometryCount: int
  ConstraintCount: int
  Support: App::PropertyLinkSub  # the plane
  MapMode: str
  addGeometry(geo: Part.Geometry, construction: bool) -> int
  addConstraint(constraint: Sketcher.Constraint) -> int
  delGeometry(index: int) -> None
  delConstraint(index: int) -> None
```

## Comparison of Approaches

| Approach | Tokens in Context | API Coverage | LLM Accuracy |
|---|---|---|---|
| Full raw docs | 400K+ (won't fit) | 100% | N/A |
| MCP execute_code | ~2-5K per query | Full (arbitrary Python) | Variable |
| MCP structured tools | ~5-10K per query | Per-tool subset | Good for supported ops |
| **FreeCAD LAP (proposed)** | **12-30K selective** | **Domain-scoped** | **Best: structured + navigable** |
| FreeCAD LAP + MCP hybrid | 12-30K + on-demand | Full | Best overall |

## Conclusions

### LAP Format Transfers Well to FreeCAD

The LAP format -- already extended for Fusion's OOP SDK -- maps naturally to FreeCAD.
The core syntax (class inheritance, properties, methods, graph navigation, gotchas) works
directly. FreeCAD-specific adaptations needed are relatively minor:

1. **Type string annotations** -- document the `'Module::Class'` strings required by
   `addObject()`
2. **Property type system** -- annotate FreeCAD's property types
   (`App::PropertyLength`, `App::PropertyLink`, etc.)
3. **Module-based domain partitioning** -- more domains than Fusion due to workbench
   fragmentation
4. **Manual recompute pattern** -- prominently document in gotchas and patterns

### Key Advantages Over Fusion LAP

- **Open source stubs** -- `freecad-stubs` package on PyPI, freely available
- **Open source docs** -- Wiki and Doxygen docs are all public and scrapable
- **Headless testing** -- Can validate generated scripts via `FreeCADCmd` without a GUI
- **Multiple doc sources** -- Wiki Markdown + Doxygen HTML + RTD Sphinx docs provide
  rich enrichment data

### Recommended Next Steps

1. **Adapt the Fusion LAP converter** for FreeCAD's stubs format and module structure
2. **Parse `freecad-stubs`** from PyPI as the primary type source
3. **Scrape FreeCAD wiki/Doxygen** for descriptions and enrichment
4. **Partition into ~14 domain files** following the workbench-based strategy
5. **Add type string registry** as a FreeCAD-specific extension
6. **Benchmark** token counts and LLM accuracy vs raw docs and MCP approaches
7. **Consider MCP integration** -- serve LAP files through an MCP server

## Sources

- [LAPIS Paper (arXiv)](https://arxiv.org/abs/2602.18541)
- [Fusion LAP SDK](https://github.com/halletj/fusion-lap-sdk)
- [FreeCAD Source Documentation (Doxygen)](https://freecad.github.io/SourceDoc/)
- [FreeCAD Python API (ReadTheDocs)](https://freecad-python-api.readthedocs.io/)
- [FreeCAD API Wiki](https://wiki.freecadweb.org/FreeCAD_API)
- [FreeCAD Scripting Basics](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/FreeCAD_Scripting_Basics.md)
- [FreeCAD Part Scripting](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Part_scripting.md)
- [FreeCAD Developers Handbook - Python Stubs](https://freecad.github.io/DevelopersHandbook/technical/PythonStubsPackage.html)
- [freecad-stubs on PyPI](https://pypi.org/project/freecad-stubs/)
- [ostr00000/freecad-stubs (GitHub)](https://github.com/ostr00000/freecad-stubs)
- [FreeCAD-documentation (GitHub)](https://github.com/FreeCAD/FreeCAD-documentation)
- [neka-nat/freecad-mcp](https://github.com/neka-nat/freecad-mcp)
- [contextform/freecad-mcp](https://github.com/contextform/freecad-mcp)
- [proximile/FreeCAD-MCP](https://github.com/proximile/FreeCAD-MCP)
- [FreeCAD Version 1.0 Release Notes](https://wiki.freecad.org/Release_notes_1.0)
- [Topological Naming Fix](https://www.ondsel.com/blog/toponaming-problem-is-history/)
- [DeepWiki FreeCAD](https://deepwiki.com/FreeCAD/FreeCAD)
