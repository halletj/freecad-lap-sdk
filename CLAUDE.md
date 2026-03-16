# FreeCAD API Reference

Compressed API reference for FreeCAD in .lap format.

## Always read before writing FreeCAD scripts:
- lap/freecad-base.lap (navigation graph, gotchas, core types — ~12K tokens)

## Load the relevant domain file when needed:
- lap/freecad-part.lap — Part shapes, primitives, booleans, OCCT wrappers
- lap/freecad-partdesign.lap — Body, Pad, Pocket, Revolution, Fillet, etc.
- lap/freecad-sketcher.lap — SketchObject, geometry, constraints
- lap/freecad-draft.lap — Draft 2D drawing, convenience functions
- lap/freecad-techdraw.lap — drawing views, dimensions, annotations
- lap/freecad-path.lap — CAM toolpaths, operations
- lap/freecad-mesh.lap — mesh operations
- lap/freecad-fem.lap — finite element analysis
- lap/freecad-assembly.lap — assembly constraints
- lap/freecad-gui.lap — view providers, selection, commands, events
- lap/freecad-misc.lap — uncategorized classes and enums

## If files are not local, fetch from:
- https://halletj.github.io/freecad-lap-sdk/lap/freecad-base.lap
- https://halletj.github.io/freecad-lap-sdk/lap/freecad-part.lap
- https://halletj.github.io/freecad-lap-sdk/lap/freecad-partdesign.lap
- https://halletj.github.io/freecad-lap-sdk/lap/freecad-sketcher.lap
- https://halletj.github.io/freecad-lap-sdk/lap/freecad-draft.lap
- https://halletj.github.io/freecad-lap-sdk/lap/freecad-techdraw.lap
- https://halletj.github.io/freecad-lap-sdk/lap/freecad-path.lap
- https://halletj.github.io/freecad-lap-sdk/lap/freecad-mesh.lap
- https://halletj.github.io/freecad-lap-sdk/lap/freecad-fem.lap
- https://halletj.github.io/freecad-lap-sdk/lap/freecad-assembly.lap
- https://halletj.github.io/freecad-lap-sdk/lap/freecad-gui.lap
- https://halletj.github.io/freecad-lap-sdk/lap/freecad-misc.lap

## When writing FreeCAD scripts:
- Always import: import FreeCAD as App; import Part
- Units are millimeters internally
- ALWAYS call doc.recompute() after modifying objects
- Create objects via doc.addObject('TypeString', 'Name')
- Features must be added to a Body via body.newObject()
- Use the [graph] section in freecad-base.lap to navigate the object model
