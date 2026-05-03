"""Tests for ``lemma.cli.uv_bootstrap``."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from lemma.cli import uv_bootstrap as ub


def _minimal_repo(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "lemma"\n', encoding="utf-8")
    lean = tmp_path / "lemma" / "lean"
    lean.mkdir(parents=True)
    (lean / "sandbox.py").write_text("# stub\n", encoding="utf-8")
    if sys.platform == "win32":
        py = tmp_path / ".venv" / "Scripts"
        py.mkdir(parents=True)
        (py / "python.exe").write_bytes(b"")
    else:
        py = tmp_path / ".venv" / "bin"
        py.mkdir(parents=True)
        (py / "python").write_bytes(b"")
    return tmp_path


def test_lemma_repo_root_finds_checkout() -> None:
    root = Path(ub.__file__).resolve().parent.parent.parent
    assert ub._lemma_repo_root(Path(ub.__file__).resolve().parent) == root


def test_maybe_reexec_calls_uv_run_when_not_in_venv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = _minimal_repo(tmp_path)
    monkeypatch.setattr(ub, "__file__", str(repo / "lemma" / "cli" / "uv_bootstrap.py"))
    monkeypatch.setenv("LEMMA_NO_UV_REEXEC", "")
    monkeypatch.delenv("LEMMA_UV_REEXEC", raising=False)
    monkeypatch.setattr(sys, "executable", "/usr/bin/python3")
    monkeypatch.setattr(sys, "argv", ["lemma"])

    captured: list[tuple[str, list[str]]] = []

    def fake_execvp(cmd: str, argv: list[str]) -> None:
        captured.append((cmd, argv))
        raise SystemExit(0)

    monkeypatch.setattr(os, "execvp", fake_execvp)
    monkeypatch.setattr(ub.shutil, "which", lambda _name: "/fake/uv")

    with pytest.raises(SystemExit) as excinfo:
        ub.maybe_reexec_under_uv()
    assert excinfo.value.code == 0
    assert len(captured) == 1
    cmd, argv = captured[0]
    assert cmd == "/fake/uv"
    assert argv == ["/fake/uv", "run", "--project", str(repo), "lemma"]


def test_maybe_reexec_skips_when_same_interpreter(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = _minimal_repo(tmp_path)
    monkeypatch.setattr(ub, "__file__", str(repo / "lemma" / "cli" / "uv_bootstrap.py"))
    if sys.platform == "win32":
        venv_py = repo / ".venv" / "Scripts" / "python.exe"
    else:
        venv_py = repo / ".venv" / "bin" / "python"
    monkeypatch.setattr(sys, "executable", str(venv_py))

    with patch.object(os, "execvp", side_effect=AssertionError("should not re-exec")):
        ub.maybe_reexec_under_uv()


def test_maybe_reexec_skips_when_no_uv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = _minimal_repo(tmp_path)
    monkeypatch.setattr(ub, "__file__", str(repo / "lemma" / "cli" / "uv_bootstrap.py"))
    monkeypatch.setattr(sys, "executable", "/usr/bin/python3")
    monkeypatch.setattr(ub.shutil, "which", lambda _name: None)

    with patch.object(os, "execvp", side_effect=AssertionError("should not re-exec")):
        ub.maybe_reexec_under_uv()
