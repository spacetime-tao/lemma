"""try-prover Lean backend resolution (host vs Docker default)."""

from pathlib import Path

import pytest
from lemma.cli.try_prover import resolve_try_prover_use_docker, resolve_try_prover_workspace_cache
from lemma.common.config import LemmaSettings


def test_resolve_use_docker_explicit_overrides_auto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEMMA_TRY_PROVER_DOCKER_VERIFY", raising=False)
    monkeypatch.setenv("PATH", "/usr/bin")
    assert resolve_try_prover_use_docker(verify=True, explicit_use_docker=True) is True
    assert resolve_try_prover_use_docker(verify=True, explicit_use_docker=False) is False


def test_resolve_use_docker_verify_uses_base_even_when_lake_on_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`try-prover --verify` follows LEMMA_USE_DOCKER; host lake is not auto-picked from PATH."""
    monkeypatch.delenv("LEMMA_TRY_PROVER_DOCKER_VERIFY", raising=False)
    monkeypatch.delenv("LEMMA_TRY_PROVER_HOST_VERIFY", raising=False)
    assert resolve_try_prover_use_docker(verify=True, explicit_use_docker=None, base_use_docker=True) is True
    assert resolve_try_prover_use_docker(verify=True, explicit_use_docker=None, base_use_docker=False) is False


def test_resolve_use_docker_env_host_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEMMA_TRY_PROVER_DOCKER_VERIFY", raising=False)
    monkeypatch.setenv("LEMMA_TRY_PROVER_HOST_VERIFY", "1")
    assert (
        resolve_try_prover_use_docker(
            verify=True,
            explicit_use_docker=None,
            base_use_docker=True,
            allow_host_lean=True,
        )
        is False
    )


def test_resolve_host_verify_ignored_without_allow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEMMA_TRY_PROVER_DOCKER_VERIFY", raising=False)
    monkeypatch.setenv("LEMMA_TRY_PROVER_HOST_VERIFY", "1")
    assert (
        resolve_try_prover_use_docker(
            verify=True,
            explicit_use_docker=None,
            base_use_docker=True,
            allow_host_lean=False,
        )
        is True
    )


def test_resolve_use_docker_env_forces_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEMMA_TRY_PROVER_DOCKER_VERIFY", "1")
    monkeypatch.setenv("LEMMA_TRY_PROVER_HOST_VERIFY", "1")
    assert resolve_try_prover_use_docker(verify=True, explicit_use_docker=None, base_use_docker=False) is True


def test_resolve_use_docker_respects_base_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEMMA_TRY_PROVER_DOCKER_VERIFY", raising=False)
    monkeypatch.delenv("LEMMA_TRY_PROVER_HOST_VERIFY", raising=False)
    assert (
        resolve_try_prover_use_docker(verify=True, explicit_use_docker=None, base_use_docker=False) is False
    )


def test_resolve_workspace_cache_defaults_under_xdg_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("LEMMA_TRY_PROVER_NO_WORKSPACE_CACHE", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    s = LemmaSettings().model_copy(update={"lean_verify_workspace_cache_dir": None})
    assert resolve_try_prover_workspace_cache(s) == tmp_path / "lemma-lean-workspace"


def test_resolve_workspace_cache_respects_explicit_env_path(tmp_path: Path) -> None:
    d = tmp_path / "custom"
    s = LemmaSettings().model_copy(update={"lean_verify_workspace_cache_dir": d})
    assert resolve_try_prover_workspace_cache(s) == d


def test_resolve_workspace_cache_disabled_by_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LEMMA_TRY_PROVER_NO_WORKSPACE_CACHE", "1")
    s = LemmaSettings().model_copy(update={"lean_verify_workspace_cache_dir": None})
    assert resolve_try_prover_workspace_cache(s) is None
