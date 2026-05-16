"""Path mapping for long-lived Docker worker (docker exec)."""

from pathlib import Path

from lemma.lean.sandbox import docker_worker_container_path


def test_docker_worker_container_path_relative(tmp_path: Path) -> None:
    root = tmp_path / "cache"
    slot = root / "template123"
    slot.mkdir(parents=True)
    assert docker_worker_container_path(slot, root, Path("/lemma-workspace")) == "/lemma-workspace/template123"


def test_docker_worker_nested_temp(tmp_path: Path) -> None:
    root = tmp_path / "cache"
    work = root / "lemma-lean-abc" / "nested"
    work.mkdir(parents=True)
    assert docker_worker_container_path(work, root, Path("/lemma-workspace")) == (
        "/lemma-workspace/lemma-lean-abc/nested"
    )
