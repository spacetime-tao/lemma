"""Compare-only Lean proof metrics helpers."""

from pathlib import Path

from lemma.lean.proof_metrics import (
    PROOF_METRICS_FILE,
    LeanProofMetrics,
    docker_proof_metrics_shell_fragment,
    parse_proof_metrics_line,
    proof_declaration_structure,
    proof_metrics_from_probe_output,
    proof_metrics_probe_source,
)
from lemma.lean.workspace import materialize_workspace
from lemma.problems.base import Problem


def _minimal_problem() -> Problem:
    return Problem(
        id="gen/test_k",
        theorem_name="t_test",
        type_expr="True",
        split="easy",
        lean_toolchain="leanprover/lean4:v4.30.0-rc2",
        mathlib_rev="5450b53e5ddc",
        imports=("Mathlib",),
    )


def test_proof_metrics_probe_source_prints_submission_theorem() -> None:
    src = proof_metrics_probe_source("t_test")
    assert "import Submission" in src
    assert "set_option pp.all true" in src
    assert "#print Submission.t_test" in src


def test_proof_metrics_from_probe_output_counts_bytes_and_lines() -> None:
    metrics = proof_metrics_from_probe_output("α\n(beta)\n", exit_code=0)
    assert metrics == LeanProofMetrics(
        proof_declaration_bytes=len("α\n(beta)\n".encode()),
        proof_declaration_lines=2,
        probe_exit_code=0,
        proof_declaration_delimiters=1,
        proof_declaration_max_depth=1,
    )


def test_proof_declaration_structure_counts_delimiter_shape() -> None:
    assert proof_declaration_structure("f (g [h {x}])") == (3, 3)
    assert proof_declaration_structure("plain long name with no delimiters") == (0, 0)


def test_parse_proof_metrics_line_uses_last_marker() -> None:
    text = "\n".join(
        [
            "noise",
            "LEMMA_PROOF_METRICS print_decl_pp_all_v1 bytes=1 lines=1 exit=0",
            "more noise",
            "LEMMA_PROOF_METRICS print_decl_pp_all_v2 bytes=25 lines=3 exit=0 delimiters=7 max_depth=4",
        ],
    )
    metrics = parse_proof_metrics_line(text)
    assert metrics is not None
    assert metrics.source == "print_decl_pp_all_v2"
    assert metrics.proof_declaration_bytes == 25
    assert metrics.proof_declaration_lines == 3
    assert metrics.probe_exit_code == 0
    assert metrics.proof_declaration_delimiters == 7
    assert metrics.proof_declaration_max_depth == 4


def test_parse_proof_metrics_line_accepts_legacy_marker() -> None:
    metrics = parse_proof_metrics_line("LEMMA_PROOF_METRICS print_decl_pp_all_v1 bytes=25 lines=3 exit=0")
    assert metrics is not None
    assert metrics.source == "print_decl_pp_all_v1"
    assert metrics.proof_declaration_delimiters is None
    assert metrics.proof_declaration_max_depth is None


def test_docker_proof_metrics_shell_fragment_is_non_failing_probe() -> None:
    frag = docker_proof_metrics_shell_fragment()
    assert "set +e" in frag
    assert "LEMMA_PROOF_METRICS print_decl_pp_all_v2" in frag
    assert "delimiters=%s max_depth=%s" in frag
    assert "lake env lean ProofMetrics.lean" in frag


def test_materialize_workspace_writes_probe_only_when_requested(tmp_path: Path) -> None:
    p = _minimal_problem()
    a = tmp_path / "without"
    b = tmp_path / "with"

    materialize_workspace(a, p, "namespace Submission\n", include_proof_metrics_probe=False)
    materialize_workspace(b, p, "namespace Submission\n", include_proof_metrics_probe=True)

    assert not (a / PROOF_METRICS_FILE).exists()
    assert (b / PROOF_METRICS_FILE).read_text(encoding="utf-8") == proof_metrics_probe_source("t_test")
