"""Docker worker name passed explicitly (LemmaSettings / `.env`)."""

from lemma.lean.sandbox import LeanSandbox


def test_docker_worker_kwarg_not_os_env() -> None:
    sb = LeanSandbox(use_docker=True, docker_worker="my-worker")
    assert sb.docker_worker == "my-worker"
