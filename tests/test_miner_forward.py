from __future__ import annotations

from inspect import Signature, signature
from pathlib import Path
from types import SimpleNamespace
from typing import Tuple  # noqa: UP035

from lemma.common.config import LemmaSettings
from lemma.miner.forward import make_forward
from lemma.miner.service import _dashboard_acceptances, _dashboard_json_url, _miner_blacklist, _zero_priority
from lemma.problems.factory import resolve_problem
from lemma.protocol import LemmaChallenge
from lemma.submissions import save_pending_submission


def _settings(tmp_path: Path) -> LemmaSettings:
    return LemmaSettings(
        _env_file=None,
        miner_submissions_path=tmp_path / "submissions.json",
        solved_ledger_path=tmp_path / "ledger.jsonl",
        target_genesis_block=10,
        commit_window_blocks=2,
    )


def _chain_block(monkeypatch, block: int) -> None:
    monkeypatch.setattr(
        "lemma.miner.forward.get_subtensor",
        lambda settings: SimpleNamespace(get_current_block=lambda: block),
    )


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


def test_miner_axon_handlers_have_runtime_synapse_annotations(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    expected = Signature.from_callable(lambda synapse: None).replace(
        parameters=[
            next(iter(signature(make_forward(settings)).parameters.values())).replace(annotation=LemmaChallenge),
        ],
    )

    assert signature(make_forward(settings)).parameters["synapse"].annotation is LemmaChallenge
    assert signature(_miner_blacklist(settings)) == expected.replace(return_annotation=Tuple[bool, str])  # noqa: UP006
    assert signature(_zero_priority) == expected.replace(return_annotation=float)


def test_dashboard_json_url_uses_public_dashboard_origin(tmp_path: Path) -> None:
    settings = _settings(tmp_path).model_copy(update={"public_dashboard_url": "https://lemmasub.net/miners/"})

    assert _dashboard_json_url(settings) == "https://lemmasub.net/data/miner-dashboard.json"


def test_dashboard_acceptance_matches_local_hotkey_and_proof() -> None:
    data = {
        "active_target": {"id": "known/test/target_2"},
        "accepted_proof_receipts": [
            {
                "target_id": "known/test/target_1",
                "solver_uid": 7,
                "solver_hotkey": "hotkey-7",
                "proof_sha256": "a" * 64,
            },
        ],
    }

    accepted = _dashboard_acceptances(data, miner_hotkey="hotkey-7", proof_hashes={"a" * 64})

    assert accepted == [
        {
            "target_id": "known/test/target_1",
            "solver_uid": 7,
            "proof_sha256": "a" * 64,
            "next_target": "known/test/target_2",
        },
    ]


async def test_miner_returns_stored_proof_for_matching_target(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _chain_block(monkeypatch, 12)
    problem = resolve_problem(settings, "known/smoke/nat_two_plus_two_eq_four")
    save_pending_submission(
        settings.miner_submissions_path,
        problem,
        "import Mathlib\n",
        proof_nonce="n" * 64,
        commitment_hash="c" * 64,
        commitment_status="committed",
    )

    resp = await make_forward(settings)(_challenge(settings))

    assert resp.proof_script == "import Mathlib\n"
    assert resp.proof_nonce == "n" * 64
    assert resp.commitment_hash == "c" * 64


async def test_miner_returns_no_proof_during_commit_phase(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _chain_block(monkeypatch, 10)
    problem = resolve_problem(settings, "known/smoke/nat_two_plus_two_eq_four")
    save_pending_submission(
        settings.miner_submissions_path,
        problem,
        "import Mathlib\n",
        proof_nonce="n" * 64,
        commitment_hash="c" * 64,
        commitment_status="committed",
    )

    resp = await make_forward(settings)(_challenge(settings))

    assert resp.proof_script is None
    assert resp.proof_nonce is None
    assert resp.commitment_hash is None


async def test_miner_returns_no_proof_without_matching_submission(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _chain_block(monkeypatch, 12)

    resp = await make_forward(settings)(_challenge(settings))

    assert resp.proof_script is None


async def test_miner_rejects_target_statement_mismatch(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    synapse = _challenge(settings).model_copy(update={"theorem_statement": "different"})

    resp = await make_forward(settings)(synapse)

    assert resp.proof_script is None
    assert resp.axon.status_code == 400
