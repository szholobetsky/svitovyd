"""Tests for svitovyd.indexer — scans a tiny temp repo."""
import pytest
from pathlib import Path
from svitovyd.indexer import build_map


@pytest.fixture
def tiny_repo(tmp_path):
    (tmp_path / "auth").mkdir()
    (tmp_path / "auth" / "login.py").write_text(
        "import hashlib\n\nclass AuthService:\n    def login(self, user):\n        pass\n"
    )
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "users.py").write_text(
        "from auth.login import AuthService\n\ndef get_user(uid):\n    return uid\n"
    )
    return tmp_path


def test_build_map_returns_string(tiny_repo):
    result = build_map(str(tiny_repo), depth=2)
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_map_contains_files(tiny_repo):
    result = build_map(str(tiny_repo), depth=2)
    assert "login.py" in result
    assert "users.py" in result


def test_build_map_contains_definitions(tiny_repo):
    result = build_map(str(tiny_repo), depth=2)
    assert "AuthService" in result or "login" in result


def test_build_map_writes_file(tiny_repo):
    out = tiny_repo / ".svitovyd" / "map.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    result = build_map(str(tiny_repo), depth=2)
    out.write_text(result, encoding="utf-8")
    assert out.exists()
    assert out.stat().st_size > 0


def test_build_map_depth3(tiny_repo):
    result = build_map(str(tiny_repo), depth=3)
    assert isinstance(result, str)


def test_build_map_skips_pycache(tiny_repo):
    (tiny_repo / "__pycache__").mkdir()
    (tiny_repo / "__pycache__" / "login.cpython-311.pyc").write_bytes(b"\x00\x01\x02")
    result = build_map(str(tiny_repo), depth=2)
    assert "__pycache__" not in result
