"""Tests for stub auto-discovery."""

import os
from unittest.mock import patch
from freecad_lap.discover import find_stubs, StubSource


def test_find_stubs_returns_stub_source():
    result = find_stubs()
    assert result is None or isinstance(result, StubSource)


def test_stub_source_has_path_and_kind():
    src = StubSource(path="/fake/path", kind="pip_stubs")
    assert src.path == "/fake/path"
    assert src.kind == "pip_stubs"


def test_find_stubs_respects_env_var(tmp_path):
    stubs_dir = tmp_path
    (stubs_dir / "FreeCAD.pyi").write_text("# stub")

    with patch.dict(os.environ, {"FREECAD_STUBS_PATH": str(stubs_dir)}):
        result = find_stubs()
    assert result is not None
    assert result.kind == "freecad_env"
