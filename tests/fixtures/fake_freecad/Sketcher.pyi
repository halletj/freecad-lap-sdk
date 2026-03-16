import FreeCAD
import Part

class SketchObject(Part.Feature):
    """A constraint-based 2D sketch object."""
    @property
    def GeometryCount(self) -> int: ...
    @property
    def ConstraintCount(self) -> int: ...
    @property
    def Support(self) -> FreeCAD.DocumentObject: ...
    @property
    def MapMode(self) -> str: ...
    def addGeometry(self, geo: Part.Shape, construction: bool = False) -> int: ...
    def addConstraint(self, constraint: 'Constraint') -> int: ...
    def delGeometry(self, index: int) -> None: ...
    def delConstraint(self, index: int) -> None: ...

class Constraint:
    """A geometric or dimensional constraint."""
    @property
    def Type(self) -> str: ...
    @property
    def Value(self) -> float: ...
    @property
    def First(self) -> int: ...
    @property
    def Second(self) -> int: ...
    def __init__(self, type: str, *args) -> None: ...

class ConstraintType:
    Coincident = "Coincident"
    Horizontal = "Horizontal"
    Vertical = "Vertical"
    Parallel = "Parallel"
    Perpendicular = "Perpendicular"
    Tangent = "Tangent"
    Equal = "Equal"
    Symmetric = "Symmetric"
    Distance = "Distance"
    DistanceX = "DistanceX"
    DistanceY = "DistanceY"
    Radius = "Radius"
    Angle = "Angle"
    Fixed = "Fixed"
