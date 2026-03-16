"""Intermediate representation for FreeCAD API classes, methods, and properties."""

from dataclasses import dataclass, field


@dataclass
class PropertyDef:
    name: str
    type: str = ""
    description: str = ""
    read_only: bool = False


@dataclass
class MethodDef:
    name: str
    args: list[tuple[str, str]] = field(default_factory=list)  # [(name, type), ...]
    returns: str = ""
    static: bool = False
    description: str = ""


@dataclass
class ClassDef:
    name: str
    namespace: str = ""
    parent: str = ""
    description: str = ""
    properties: dict[str, PropertyDef] = field(default_factory=dict)
    methods: dict[str, MethodDef] = field(default_factory=dict)
    events: list[str] = field(default_factory=list)
    is_collection: bool = False
    collection_item_type: str = ""


@dataclass
class EnumDef:
    name: str
    namespace: str = ""
    values: list[str] = field(default_factory=list)
    description: str = ""


class IR:
    """Intermediate representation of the entire FreeCAD API."""

    def __init__(self):
        self.namespaces: dict[str, dict[str, ClassDef]] = {}
        self.enums: dict[str, dict[str, EnumDef]] = {}
        self.examples: list[dict] = []
        self.gotchas: list[str] = []

    def add_class(self, cls: ClassDef):
        ns = cls.namespace or "_unknown"
        if ns not in self.namespaces:
            self.namespaces[ns] = {}
        self.namespaces[ns][cls.name] = cls

    def add_enum(self, enum: EnumDef):
        ns = enum.namespace or "_unknown"
        if ns not in self.enums:
            self.enums[ns] = {}
        self.enums[ns][enum.name] = enum

    def merge_class(self, enrichment: ClassDef):
        """Merge enrichment data into an existing class. Enrichment fills gaps but doesn't overwrite."""
        ns = enrichment.namespace or "_unknown"
        if ns not in self.namespaces or enrichment.name not in self.namespaces[ns]:
            self.add_class(enrichment)
            return

        existing = self.namespaces[ns][enrichment.name]
        if enrichment.description and not existing.description:
            existing.description = enrichment.description
        if enrichment.parent and not existing.parent:
            existing.parent = enrichment.parent
        for prop_name, prop in enrichment.properties.items():
            if prop_name not in existing.properties:
                existing.properties[prop_name] = prop
            else:
                if prop.description and not existing.properties[prop_name].description:
                    existing.properties[prop_name].description = prop.description
                if prop.type and not existing.properties[prop_name].type:
                    existing.properties[prop_name].type = prop.type
        for method_name, method in enrichment.methods.items():
            if method_name not in existing.methods:
                existing.methods[method_name] = method
            else:
                if method.description and not existing.methods[method_name].description:
                    existing.methods[method_name].description = method.description

    def all_classes(self) -> list[ClassDef]:
        result = []
        for ns_classes in self.namespaces.values():
            result.extend(ns_classes.values())
        return result

    def all_enums(self) -> list[EnumDef]:
        result = []
        for ns_enums in self.enums.values():
            result.extend(ns_enums.values())
        return result
