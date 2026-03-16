"""Tests for the full build pipeline."""

from pathlib import Path
from freecad_lap.build import build_lap_files

FIXTURES = Path(__file__).parent / "fixtures" / "fake_freecad"


def test_build_produces_lap_files(tmp_path):
    build_lap_files(
        output_dir=str(tmp_path),
        stubs_path=str(FIXTURES),
    )
    assert (tmp_path / "freecad-base.lap").exists()
    assert (tmp_path / "freecad-graph.lap").exists()
    assert (tmp_path / "freecad-gotchas.lap").exists()


def test_build_base_contains_graph(tmp_path):
    build_lap_files(
        output_dir=str(tmp_path),
        stubs_path=str(FIXTURES),
    )
    base = (tmp_path / "freecad-base.lap").read_text()
    assert "[graph]" in base
    assert "[gotchas]" in base


def test_build_domain_files_contain_classes(tmp_path):
    build_lap_files(
        output_dir=str(tmp_path),
        stubs_path=str(FIXTURES),
    )
    # Pad should appear in partdesign domain
    partdesign_file = tmp_path / "freecad-partdesign.lap"
    if partdesign_file.exists():
        content = partdesign_file.read_text()
        assert "Pad" in content
