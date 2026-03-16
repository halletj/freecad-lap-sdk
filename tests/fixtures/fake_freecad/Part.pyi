import FreeCAD

class Shape:
    """A geometric shape."""
    @property
    def Faces(self) -> list['Face']: ...
    @property
    def Edges(self) -> list['Edge']: ...
    @property
    def Vertexes(self) -> list['Vertex']: ...
    @property
    def Wires(self) -> list['Wire']: ...
    @property
    def ShapeType(self) -> str: ...
    @property
    def Volume(self) -> float: ...
    @property
    def Area(self) -> float: ...
    def fuse(self, other: 'Shape') -> 'Shape': ...
    def cut(self, other: 'Shape') -> 'Shape': ...
    def common(self, other: 'Shape') -> 'Shape': ...
    def exportStep(self, filename: str) -> None: ...
    def exportStl(self, filename: str) -> None: ...

class Feature(FreeCAD.GeoFeature):
    @property
    def Shape(self) -> Shape: ...

class Face(Shape):
    @property
    def Surface(self) -> 'Surface': ...

class Edge(Shape):
    @property
    def Curve(self) -> 'Curve': ...

class Vertex(Shape):
    @property
    def Point(self) -> FreeCAD.Vector: ...

class Wire(Shape):
    @property
    def Edges(self) -> list[Edge]: ...

class Shell(Shape):
    pass

class Solid(Shape):
    pass

class Compound(Shape):
    pass

class Box(Feature):
    @property
    def Length(self) -> float: ...
    @property
    def Width(self) -> float: ...
    @property
    def Height(self) -> float: ...

class Cylinder(Feature):
    @property
    def Radius(self) -> float: ...
    @property
    def Height(self) -> float: ...

class Sphere(Feature):
    @property
    def Radius(self) -> float: ...

class LineSegment:
    """A line segment geometry."""
    def __init__(self, start: FreeCAD.Vector, end: FreeCAD.Vector) -> None: ...

class Circle:
    """A circle geometry."""
    def __init__(self, center: FreeCAD.Vector, normal: FreeCAD.Vector, radius: float) -> None: ...

class ArcOfCircle:
    """An arc of a circle."""
    def __init__(self, circle: Circle, start: float, end: float) -> None: ...

class BSplineCurve:
    def poles(self) -> list[FreeCAD.Vector]: ...
    def knots(self) -> list[float]: ...

class ShapeType:
    Solid = "Solid"
    Shell = "Shell"
    Face = "Face"
    Wire = "Wire"
    Edge = "Edge"
    Vertex = "Vertex"
    Compound = "Compound"
