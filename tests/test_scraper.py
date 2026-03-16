"""Tests for wiki scraper."""

from pathlib import Path
from freecad_lap.scraper import parse_api_page
from freecad_lap.ir import ClassDef

FIXTURES = Path(__file__).parent / "fixtures" / "wiki"


def test_parse_api_page():
    markdown = (FIXTURES / "PartDesign_Pad.md").read_text()
    cls = parse_api_page("Pad", markdown)
    assert isinstance(cls, ClassDef)
    assert cls.name == "Pad"
    assert "extrude" in cls.description.lower() or "pad" in cls.description.lower()


def test_parse_api_page_properties():
    markdown = (FIXTURES / "PartDesign_Pad.md").read_text()
    cls = parse_api_page("Pad", markdown)
    assert "Length" in cls.properties
    assert "Profile" in cls.properties


def test_parse_api_page_methods():
    markdown = (FIXTURES / "PartDesign_Pad.md").read_text()
    cls = parse_api_page("Pad", markdown)
    assert "execute" in cls.methods
