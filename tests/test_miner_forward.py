from __future__ import annotations

from pathlib import Path

from lemma.common.config import LemmaSettings
from lemma.miner.forward import make_forward
from lemma.problems.factory import resolve_problem
from lemma.protocol import LemmaChallenge
from lemma.submissions import save_pending_submission


def _settings(tmp_path: Path) -> LemmaSettings:
    return LemmaSettings(_env_file=None, miner_submissions_path=tmp_path / "submissions.json")


def _challenge(settings: LemmaSettings, problem_id: str = "known/smoke/nat_two_plus_two_eq_four") -> LemmaChallenge:
    problem = resolve_problem(settings, problem_id)
    return LemmaChallenge(
        theorem_id=problem.id,
        theorem_statement=problem.challenge_source(),
        imports=list(problem.imports),
        lean_toolchain=problem.lean_toolchain,
        mathlib_rev=problem.mathlib_rev,
        poll_id="poll-1",
    )


async def test_miner_returns_stored_proof_for_matching_target(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    problem = resolve_problem(settings, "known/smoke/nat_two_plus_two_eq_four")
    save_pending_submission(settings.miner_submissions_path, problem, "import Mathlib\n")

    resp = await make_forward(settings)(_challenge(settings))

    assert resp.proof_script == "import Mathlib\n"


async def test_miner_returns_no_proof_without_matching_submission(tmp_path: Path) -> None:
    settings = _settings(tmp_path)

    resp = await make_forward(settings)(_challenge(settings))

    assert resp.proof_script is None


async def test_miner_rejects_target_statement_mismatch(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    synapse = _challenge(settings).model_copy(update={"theorem_statement": "different"})

    resp = await make_forward(settings)(synapse)

    assert resp.proof_script is None
    assert resp.axon.status_code == 400
