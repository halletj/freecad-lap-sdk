"""Tests for MCP server tool functions."""

from freecad_lap.mcp_server import lookup_domain, search_lap, get_graph


def test_lookup_domain(tmp_path):
    (tmp_path / "freecad-part.lap").write_text("[classes]\nShape\n  Faces: list[Face]\n")
    result = lookup_domain("part", str(tmp_path))
    assert "Shape" in result


def test_lookup_domain_not_found(tmp_path):
    result = lookup_domain("nonexistent", str(tmp_path))
    assert "not found" in result.lower()


def test_search_lap(tmp_path):
    (tmp_path / "freecad-partdesign.lap").write_text("[classes]\nPad : Feature\n  Length: float\n")
    (tmp_path / "freecad-part.lap").write_text("[classes]\nShape\n")
    results = search_lap("Pad", str(tmp_path))
    assert "Pad" in results
    assert "freecad-partdesign.lap" in results


def test_get_graph(tmp_path):
    (tmp_path / "freecad-graph.lap").write_text("[graph]\nFreeCAD (App)\n  .ActiveDocument -> Document\n")
    result = get_graph(str(tmp_path))
    assert "FreeCAD" in result
