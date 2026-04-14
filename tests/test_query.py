"""Tests for svitovyd.query — uses synthetic map content, no scan required."""
import pytest
import tempfile
import os
from svitovyd.query import parse_map, find_map, trace_map, deps_map, sym_report


MAP_CONTENT = """\
auth/login.py
  defines : login(ln:5), validate_token(ln:12)
  call:get_user  -> api/users.py
  import:hashlib -> stdlib/hashlib.py

api/users.py
  defines : get_user(ln:3), create_user(ln:15)
  call:login     -> auth/login.py
  import:db      -> db/connection.py

db/connection.py
  defines : connect(ln:1), disconnect(ln:8)
"""


@pytest.fixture
def map_file(tmp_path):
    p = tmp_path / "map.txt"
    p.write_text(MAP_CONTENT, encoding="utf-8")
    return str(p)


def test_parse_map_returns_dicts(map_file):
    defines, links = parse_map(map_file)
    assert isinstance(defines, dict)
    assert isinstance(links, dict)


def test_parse_map_finds_definitions(map_file):
    defines, _ = parse_map(map_file)
    assert "auth/login.py" in defines
    assert "login" in defines["auth/login.py"]


def test_find_map_no_filter(map_file):
    hits, result = find_map(map_file, "")
    assert isinstance(result, str)
    assert len(result) > 0


def test_find_map_filename_filter(map_file):
    hits, result = find_map(map_file, "auth")
    hit_files = [h.splitlines()[0] for h in hits]
    assert any("auth" in f for f in hit_files)
    assert all("auth" in f for f in hit_files)


def test_find_map_exclude_filter(map_file):
    hits, result = find_map(map_file, "!auth")
    hit_files = [h.splitlines()[0] for h in hits]
    assert not any("auth" in f for f in hit_files)


def test_find_map_content_filter(map_file):
    hits, result = find_map(map_file, "\\login")
    assert len(hits) > 0


def test_trace_map_known_identifier(map_file):
    result = trace_map(map_file, "login")
    assert result is not None
    assert "login" in result


def test_trace_map_unknown_identifier(map_file):
    result = trace_map(map_file, "nonexistent_function_xyz")
    assert result is None


def test_deps_map_known(map_file):
    result = deps_map(map_file, "login")
    assert result is not None


def test_sym_report_runs(map_file):
    result = sym_report(map_file, k=3)
    assert isinstance(result, str)
    assert "ASYMMETRY" in result or "asymmetry" in result.lower() or len(result) > 0
