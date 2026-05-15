from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from lemma.commitments import build_proof_commitment, proof_sha256
from lemma.common.config import LemmaSettings
from lemma.lean.sandbox import VerifyResult
from lemma.problems.base import Problem, ProblemSource
from lemma.problems.known_theorems import known_theorems_manifest_sha256
from lemma.protocol import LemmaChallenge
from lemma.validator import epoch

PROBLEM = Problem(
    id="known/test/one",
    theorem_name="target_one",
    type_expr="True",
    split="known_theorems",
    lean_toolchain="lt",
    mathlib_rev="mr",
    imports=("Mathlib",),
)
PREVIOUS_PROBLEM = Problem(
    id="known/test/zero",
    theorem_name="target_zero",
    type_expr="True",
    split="known_theorems",
    lean_toolchain="lt",
    mathlib_rev="mr",
    imports=("Mathlib",),
)


class _OneProblemSource(ProblemSource):
    def all_problems(self) -> list[Problem]:
        return [PROBLEM]

    def sample(self, seed: int, split: str | None = None) -> Problem:
        return PROBLEM

    def get(self, problem_id: str) -> Problem:
        if problem_id != PROBLEM.id:
            raise KeyError(problem_id)
        return PROBLEM


class _TwoProblemSource(_OneProblemSource):
    def all_problems(self) -> list[Problem]:
        return [PREVIOUS_PROBLEM, PROBLEM]


class _SolvedProblemSource(_OneProblemSource):
    def sample(self, seed: int, split: str | None = None) -> Problem:
        raise ValueError("all solved")


class _Subtensor:
    def __init__(
        self,
        n: int = 2,
        *,
        current_block: int = 50,
        commitments_by_block: dict[int, dict[str, str]] | None = None,
        set_weight_results: list[object] | None = None,
    ) -> None:
        self.n = n
        self.current_block = current_block
        self.commitments_by_block = commitments_by_block or {}
        self.set_weights_calls: list[dict[str, Any]] = []
        self.set_weight_results = list(set_weight_results or [SimpleNamespace(success=True, message="ok")])

    def get_current_block(self) -> int:
        return self.current_block

    def metagraph(self, netuid: int) -> SimpleNamespace:
        return SimpleNamespace(
            n=self.n,
            axons=[SimpleNamespace(uid=uid) for uid in range(self.n)],
            hotkeys=[f"miner-hotkey-{uid}" for uid in range(self.n)],
            coldkeys=[f"miner-coldkey-{uid}" for uid in range(self.n)],
        )

    def get_uid_for_hotkey_on_subnet(self, hotkey: str, netuid: int) -> None:
        return None

    def get_all_commitments(self, netuid: int, *, block: int) -> dict[str, str]:
        return self.commitments_by_block.get(block, {})

    def set_weights(self, **kwargs: Any) -> object:
        self.set_weights_calls.append(kwargs)
        result = self.set_weight_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class _Wallet:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.hotkey = SimpleNamespace(ss58_address="validator-hotkey")


def _settings(tmp_path: Path, **updates: object) -> LemmaSettings:
    base = {
        "_env_file": None,
        "solved_ledger_path": tmp_path / "solved-ledger.jsonl",
        "validator_min_free_bytes": 0,
        "validator_abort_if_not_registered": False,
        "target_genesis_block": 48,
        "commit_window_blocks": 2,
        "owner_burn_uid": 1,
    }
    base.update(updates)
    return LemmaSettings(**base)


def _response(synapse: LemmaChallenge, *, proof: str | None = None, **updates: object) -> LemmaChallenge:
    data = {
        "theorem_id": synapse.theorem_id,
        "theorem_statement": synapse.theorem_statement,
        "imports": list(synapse.imports or []),
        "lean_toolchain": synapse.lean_toolchain,
        "mathlib_rev": synapse.mathlib_rev,
        "poll_id": synapse.poll_id,
        "proof_script": proof,
    }
    data.update(updates)
    resp = LemmaChallenge(**data)
    resp.dendrite.status_code = 200
    resp.dendrite.status_message = "Success"
    return resp


def _commitment(
    settings: LemmaSettings,
    *,
    uid: int,
    proof: str,
    nonce: str | None = None,
    problem: Problem = PROBLEM,
) -> tuple[str, str, str]:
    nonce = nonce or f"nonce-{uid}"
    commitment = build_proof_commitment(
        netuid=settings.netuid,
        miner_hotkey=f"miner-hotkey-{uid}",
        manifest_sha256=known_theorems_manifest_sha256(settings.known_theorems_manifest_path),
        problem=problem,
        proof_hash=proof_sha256(proof),
        nonce=nonce,
    )
    return nonce, commitment.commitment_hash, commitment.payload_text


def _install_epoch_fakes(
    monkeypatch,
    *,
    subtensor: _Subtensor,
    response_fn: Callable[[list[object], LemmaChallenge], list[object]],
    verify_fn: Callable[[str], VerifyResult] | None = None,
) -> None:
    class Dendrite:
        def __init__(self, *, wallet: object) -> None:
            self.wallet = wallet

        async def __aenter__(self) -> Dendrite:
            return self

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

        async def __call__(
            self,
            axons: list[object],
            synapse: LemmaChallenge,
            *,
            timeout: float,
            run_async: bool,
        ) -> list[object]:
            return response_fn(axons, synapse)

    def run_lean_verify(*args: object, **kwargs: object) -> VerifyResult:
        proof = str(kwargs["proof_script"])
        if verify_fn is None:
            return VerifyResult(passed=True, reason="ok")
        return verify_fn(proof)

    monkeypatch.setattr(epoch, "get_subtensor", lambda settings: subtensor)
    monkeypatch.setattr(epoch.bt, "Wallet", _Wallet)
    monkeypatch.setattr(epoch.bt, "Dendrite", Dendrite)
    monkeypatch.setattr(epoch, "run_lean_verify", run_lean_verify)


def _ledger_row(target_id: str, solver_uid: int) -> str:
    problem = PREVIOUS_PROBLEM if target_id == PREVIOUS_PROBLEM.id else PROBLEM
    return (
        json.dumps(
            {
                "target_id": target_id,
                "winner_uid": solver_uid,
                "winner_hotkey": f"miner-hotkey-{solver_uid}",
                "winner_coldkey": f"miner-coldkey-{solver_uid}",
                "proof_sha256": "a" * 64,
                "accepted_block": 1,
                "accepted_unix": 2,
                "validator_hotkey": "validator-hotkey",
                "lemma_version": "0.1.0",
                "verify_reason": "ok",
                "build_seconds": 0.0,
                "theorem_statement_sha256": problem.theorem_statement_sha256(),
            },
            sort_keys=True,
        )
        + "\n"
    )


def _tied_ledger_row(target_id: str, solver_uids: list[int]) -> str:
    problem = PREVIOUS_PROBLEM if target_id == PREVIOUS_PROBLEM.id else PROBLEM
    return (
        json.dumps(
            {
                "target_id": target_id,
                "solvers": [
                    {
                        "uid": uid,
                        "hotkey": f"miner-hotkey-{uid}",
                        "coldkey": f"miner-coldkey-{uid}",
                        "proof_sha256": str(uid) * 64,
                        "verify_reason": "ok",
                        "build_seconds": 0.0,
                    }
                    for uid in solver_uids
                ],
                "accepted_block": 1,
                "accepted_unix": 2,
                "validator_hotkey": "validator-hotkey",
                "lemma_version": "0.1.0",
                "theorem_statement_sha256": problem.theorem_statement_sha256(),
            },
            sort_keys=True,
        )
        + "\n"
    )


def _assert_weights(actual: dict[int, float], expected: dict[int, float]) -> None:
    assert set(actual) == set(expected)
    for uid, weight in expected.items():
        assert abs(actual[uid] - weight) < 1e-9


def test_set_weights_outcome_handles_bittensor_shapes() -> None:
    assert epoch._set_weights_outcome((False, "rate limited")) == (False, "rate limited")
    assert epoch._set_weights_outcome((True, "ok")) == (True, "ok")
    assert epoch._set_weights_outcome((False, None)) == (False, "success=False without message")
    assert epoch._set_weights_outcome({"success": False}) == (False, "success=False without message")
    assert epoch._set_weights_outcome(False) == (False, "False")

    ok, message = epoch._set_weights_outcome(SimpleNamespace(success=False, message=None))
    assert not ok
    assert message == "success=False without message"


async def test_proof_no_proof_routes_epoch_to_owner_burn_uid(monkeypatch, tmp_path: Path) -> None:
    subtensor = _Subtensor()
    _install_epoch_fakes(
        monkeypatch,
        subtensor=subtensor,
        response_fn=lambda axons, synapse: [_response(synapse, proof=None) for _axon in axons],
    )

    weights = await epoch.run_epoch(_settings(tmp_path), _TwoProblemSource(), dry_run=False)

    assert weights == {1: 1.0}
    assert subtensor.set_weights_calls[0]["weights"] == [0.0, 1.0]
    assert not (tmp_path / "solved-ledger.jsonl").exists()


async def test_invalid_owner_burn_uid_skips_weight_write(monkeypatch, tmp_path: Path) -> None:
    subtensor = _Subtensor(n=2)
    _install_epoch_fakes(
        monkeypatch,
        subtensor=subtensor,
        response_fn=lambda axons, synapse: [_response(synapse, proof=None) for _axon in axons],
    )

    weights = await epoch.run_epoch(_settings(tmp_path, owner_burn_uid=9), _TwoProblemSource(), dry_run=False)

    assert weights == {}
    assert subtensor.set_weights_calls == []


async def test_proof_single_valid_solver_gets_observed_difficulty_weight(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    proof = "namespace Submission\n-- uid 0\n"
    nonce, commitment_hash, payload = _commitment(settings, uid=0, proof=proof)
    subtensor = _Subtensor(n=2, commitments_by_block={48: {"miner-hotkey-0": payload}, 49: {"miner-hotkey-0": payload}})
    _install_epoch_fakes(
        monkeypatch,
        subtensor=subtensor,
        response_fn=lambda axons, synapse: [
            _response(synapse, proof=proof, proof_nonce=nonce, commitment_hash=commitment_hash),
            _response(synapse, proof=None),
        ],
    )

    weights = await epoch.run_epoch(settings, _TwoProblemSource(), dry_run=False)
    ledger = [json.loads(line) for line in (tmp_path / "solved-ledger.jsonl").read_text().splitlines()]

    _assert_weights(weights, {0: 0.25, 1: 0.75})
    assert ledger[0]["target_id"] == PROBLEM.id
    assert [solver["uid"] for solver in ledger[0]["solvers"]] == [0]
    assert ledger[0]["solvers"][0]["proof_script"] == "namespace Submission\n-- uid 0\n"
    assert ledger[0]["solvers"][0]["proof_nonce"] == nonce
    assert ledger[0]["solvers"][0]["commitment_hash"] == commitment_hash
    assert ledger[0]["solvers"][0]["commitment_block"] == 48
    assert subtensor.set_weights_calls[0]["weights"] == [0.25, 0.75]


async def test_proof_same_block_valid_solvers_split_rewards(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path, owner_burn_uid=3)
    proof0 = "namespace Submission\n-- uid 0\n"
    proof1 = "namespace Submission\n-- uid 1\n"
    nonce0, hash0, payload0 = _commitment(settings, uid=0, proof=proof0)
    nonce1, hash1, payload1 = _commitment(settings, uid=1, proof=proof1)
    commitments = {"miner-hotkey-0": payload0, "miner-hotkey-1": payload1}
    subtensor = _Subtensor(n=4, commitments_by_block={48: commitments, 49: commitments})
    _install_epoch_fakes(
        monkeypatch,
        subtensor=subtensor,
        response_fn=lambda axons, synapse: [
            _response(synapse, proof=proof0, proof_nonce=nonce0, commitment_hash=hash0),
            _response(synapse, proof=proof1, proof_nonce=nonce1, commitment_hash=hash1),
            _response(synapse, proof=None),
            _response(synapse, proof=None),
        ],
    )

    weights = await epoch.run_epoch(settings, _TwoProblemSource(), dry_run=False)
    ledger = [json.loads(line) for line in (tmp_path / "solved-ledger.jsonl").read_text().splitlines()]

    _assert_weights(weights, {0: 0.125, 1: 0.125, 3: 0.75})
    assert ledger[0]["target_id"] == PROBLEM.id
    assert [solver["uid"] for solver in ledger[0]["solvers"]] == [0, 1]
    assert subtensor.set_weights_calls[0]["weights"] == [0.125, 0.125, 0.0, 0.75]


async def test_proof_later_commitment_gets_lower_rank_reward(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path, owner_burn_uid=3)
    proof0 = "namespace Submission\n-- early proof\n"
    proof1 = "namespace Submission\n-- late different proof\n"
    nonce0, hash0, payload0 = _commitment(settings, uid=0, proof=proof0)
    nonce1, hash1, payload1 = _commitment(settings, uid=1, proof=proof1)
    subtensor = _Subtensor(
        n=4,
        commitments_by_block={
            48: {"miner-hotkey-0": payload0},
            49: {"miner-hotkey-0": payload0, "miner-hotkey-1": payload1},
        },
    )
    _install_epoch_fakes(
        monkeypatch,
        subtensor=subtensor,
        response_fn=lambda axons, synapse: [
            _response(synapse, proof=proof0, proof_nonce=nonce0, commitment_hash=hash0),
            _response(synapse, proof=proof1, proof_nonce=nonce1, commitment_hash=hash1),
            _response(synapse, proof=None),
            _response(synapse, proof=None),
        ],
    )

    weights = await epoch.run_epoch(settings, _TwoProblemSource(), dry_run=False)
    ledger = [json.loads(line) for line in (tmp_path / "solved-ledger.jsonl").read_text().splitlines()]

    _assert_weights(weights, {0: 1.0 / 6.0, 1: 1.0 / 12.0, 3: 0.75})
    assert [solver["uid"] for solver in ledger[0]["solvers"]] == [0, 1]


async def test_proof_duplicate_hash_credits_earliest_commitment(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path, owner_burn_uid=3)
    proof = "namespace Submission\n-- same proof\n"
    nonce0, hash0, payload0 = _commitment(settings, uid=0, proof=proof, nonce="nonce-0")
    nonce1, hash1, payload1 = _commitment(settings, uid=1, proof=proof, nonce="nonce-1")
    subtensor = _Subtensor(
        n=4,
        commitments_by_block={
            48: {"miner-hotkey-1": payload1},
            49: {"miner-hotkey-0": payload0, "miner-hotkey-1": payload1},
        },
    )
    _install_epoch_fakes(
        monkeypatch,
        subtensor=subtensor,
        response_fn=lambda axons, synapse: [
            _response(synapse, proof=proof, proof_nonce=nonce0, commitment_hash=hash0),
            _response(synapse, proof=proof, proof_nonce=nonce1, commitment_hash=hash1),
            _response(synapse, proof=None),
            _response(synapse, proof=None),
        ],
    )

    weights = await epoch.run_epoch(settings, _TwoProblemSource(), dry_run=False)
    ledger = [json.loads(line) for line in (tmp_path / "solved-ledger.jsonl").read_text().splitlines()]

    _assert_weights(weights, {0: 1.0 / 12.0, 1: 1.0 / 6.0, 3: 0.75})
    assert [solver["uid"] for solver in ledger[0]["solvers"]] == [0, 1]


async def test_proof_duplicate_hash_same_commitment_block_splits(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path, owner_burn_uid=3)
    proof = "namespace Submission\n-- same block same proof\n"
    nonce0, hash0, payload0 = _commitment(settings, uid=0, proof=proof, nonce="nonce-0")
    nonce1, hash1, payload1 = _commitment(settings, uid=1, proof=proof, nonce="nonce-1")
    commitments = {"miner-hotkey-0": payload0, "miner-hotkey-1": payload1}
    subtensor = _Subtensor(n=4, commitments_by_block={48: commitments, 49: commitments})
    _install_epoch_fakes(
        monkeypatch,
        subtensor=subtensor,
        response_fn=lambda axons, synapse: [
            _response(synapse, proof=proof, proof_nonce=nonce0, commitment_hash=hash0),
            _response(synapse, proof=proof, proof_nonce=nonce1, commitment_hash=hash1),
            _response(synapse, proof=None),
            _response(synapse, proof=None),
        ],
    )

    weights = await epoch.run_epoch(settings, _TwoProblemSource(), dry_run=False)
    ledger = [json.loads(line) for line in (tmp_path / "solved-ledger.jsonl").read_text().splitlines()]

    _assert_weights(weights, {0: 0.125, 1: 0.125, 3: 0.75})
    assert [solver["uid"] for solver in ledger[0]["solvers"]] == [0, 1]


async def test_proof_rejects_missing_or_late_commitment(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    proof = "namespace Submission\n-- late\n"
    nonce, commitment_hash, payload = _commitment(settings, uid=0, proof=proof)
    subtensor = _Subtensor(n=2, commitments_by_block={50: {"miner-hotkey-0": payload}})
    verify_calls: list[str] = []
    _install_epoch_fakes(
        monkeypatch,
        subtensor=subtensor,
        response_fn=lambda axons, synapse: [
            _response(synapse, proof=proof, proof_nonce=nonce, commitment_hash=commitment_hash),
            _response(synapse, proof=None),
        ],
        verify_fn=lambda proof: verify_calls.append(proof) or VerifyResult(passed=True, reason="ok"),
    )

    weights = await epoch.run_epoch(settings, _TwoProblemSource(), dry_run=False)

    assert weights == {1: 1.0}
    assert verify_calls == []
    assert not (tmp_path / "solved-ledger.jsonl").exists()


async def test_proof_rejects_copied_commitment_under_different_hotkey(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    proof = "namespace Submission\n-- copied\n"
    nonce, commitment_hash, payload = _commitment(settings, uid=0, proof=proof)
    subtensor = _Subtensor(
        n=2,
        commitments_by_block={48: {"miner-hotkey-1": payload}, 49: {"miner-hotkey-1": payload}},
    )
    verify_calls: list[str] = []
    _install_epoch_fakes(
        monkeypatch,
        subtensor=subtensor,
        response_fn=lambda axons, synapse: [
            _response(synapse, proof=None),
            _response(synapse, proof=proof, proof_nonce=nonce, commitment_hash=commitment_hash),
        ],
        verify_fn=lambda proof: verify_calls.append(proof) or VerifyResult(passed=True, reason="ok"),
    )

    weights = await epoch.run_epoch(settings, _TwoProblemSource(), dry_run=False)

    assert weights == {1: 1.0}
    assert verify_calls == []
    assert not (tmp_path / "solved-ledger.jsonl").exists()


async def test_proof_invalid_lean_cannot_win(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    proof = "bad proof"
    nonce0, hash0, payload0 = _commitment(settings, uid=0, proof=proof)
    nonce1, hash1, payload1 = _commitment(settings, uid=1, proof=proof)
    commitments = {"miner-hotkey-0": payload0, "miner-hotkey-1": payload1}
    subtensor = _Subtensor(commitments_by_block={48: commitments, 49: commitments})
    _install_epoch_fakes(
        monkeypatch,
        subtensor=subtensor,
        response_fn=lambda axons, synapse: [
            _response(synapse, proof=proof, proof_nonce=nonce0, commitment_hash=hash0),
            _response(synapse, proof=proof, proof_nonce=nonce1, commitment_hash=hash1),
        ],
        verify_fn=lambda proof: VerifyResult(passed=False, reason="compile_error", stderr_tail=proof),
    )

    weights = await epoch.run_epoch(settings, _TwoProblemSource(), dry_run=False)

    assert weights == {1: 1.0}
    assert subtensor.set_weights_calls[0]["weights"] == [0.0, 1.0]
    assert not (tmp_path / "solved-ledger.jsonl").exists()


async def test_proof_mismatched_response_is_ignored_before_verify(monkeypatch, tmp_path: Path) -> None:
    verify_calls: list[str] = []
    subtensor = _Subtensor()
    _install_epoch_fakes(
        monkeypatch,
        subtensor=subtensor,
        response_fn=lambda axons, synapse: [
            _response(synapse, proof="proof", theorem_statement="different") for _axon in axons
        ],
        verify_fn=lambda proof: verify_calls.append(proof) or VerifyResult(passed=True, reason="ok"),
    )

    weights = await epoch.run_epoch(_settings(tmp_path), _OneProblemSource(), dry_run=False)

    assert weights == {1: 1.0}
    assert verify_calls == []
    assert subtensor.set_weights_calls[0]["weights"] == [0.0, 1.0]


async def test_proof_existing_solver_set_does_not_keep_weights_while_next_target_unsolved(
    monkeypatch,
    tmp_path: Path,
) -> None:
    ledger_path = tmp_path / "solved-ledger.jsonl"
    ledger_path.write_text(_ledger_row("known/test/zero", 1), encoding="utf-8")
    subtensor = _Subtensor(n=2)
    _install_epoch_fakes(
        monkeypatch,
        subtensor=subtensor,
        response_fn=lambda axons, synapse: [_response(synapse, proof=None) for _axon in axons],
    )

    weights = await epoch.run_epoch(_settings(tmp_path), _TwoProblemSource(), dry_run=False)

    assert weights == {1: 1.0}
    assert subtensor.set_weights_calls[0]["weights"] == [0.0, 1.0]


async def test_proof_existing_tied_solvers_do_not_keep_split_weights(monkeypatch, tmp_path: Path) -> None:
    ledger_path = tmp_path / "solved-ledger.jsonl"
    ledger_path.write_text(_tied_ledger_row("known/test/zero", [0, 1]), encoding="utf-8")
    subtensor = _Subtensor(n=2)
    _install_epoch_fakes(
        monkeypatch,
        subtensor=subtensor,
        response_fn=lambda axons, synapse: [_response(synapse, proof=None) for _axon in axons],
    )

    weights = await epoch.run_epoch(_settings(tmp_path), _TwoProblemSource(), dry_run=False)

    assert weights == {1: 1.0}
    assert subtensor.set_weights_calls[0]["weights"] == [0.0, 1.0]


async def test_proof_duplicate_target_does_not_change_solver_set(monkeypatch, tmp_path: Path) -> None:
    ledger_path = tmp_path / "solved-ledger.jsonl"
    original = _ledger_row(PROBLEM.id, 1)
    ledger_path.write_text(original, encoding="utf-8")
    subtensor = _Subtensor(n=2)
    _install_epoch_fakes(
        monkeypatch,
        subtensor=subtensor,
        response_fn=lambda axons, synapse: [
            _response(synapse, proof=f"namespace Submission\n-- duplicate uid {axon.uid}\n") for axon in axons
        ],
    )

    weights = await epoch.run_epoch(_settings(tmp_path), _OneProblemSource(), dry_run=False)

    assert weights == {1: 1.0}
    assert ledger_path.read_text(encoding="utf-8") == original
    assert subtensor.set_weights_calls[0]["weights"] == [0.0, 1.0]


async def test_proof_stale_ledger_hash_does_not_keep_weights(monkeypatch, tmp_path: Path) -> None:
    ledger_path = tmp_path / "solved-ledger.jsonl"
    row = json.loads(_ledger_row(PREVIOUS_PROBLEM.id, 1))
    row["theorem_statement_sha256"] = "bad"
    ledger_path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    subtensor = _Subtensor(n=2)
    _install_epoch_fakes(
        monkeypatch,
        subtensor=subtensor,
        response_fn=lambda axons, synapse: [_response(synapse, proof=None) for _axon in axons],
    )

    weights = await epoch.run_epoch(_settings(tmp_path), _TwoProblemSource(), dry_run=False)

    assert weights == {1: 1.0}
    assert subtensor.set_weights_calls[0]["weights"] == [0.0, 1.0]


async def test_proof_all_targets_solved_routes_to_owner_burn_uid(monkeypatch, tmp_path: Path) -> None:
    ledger_path = tmp_path / "solved-ledger.jsonl"
    ledger_path.write_text(_ledger_row(PROBLEM.id, 0), encoding="utf-8")
    subtensor = _Subtensor(n=2)
    monkeypatch.setattr(epoch, "get_subtensor", lambda settings: subtensor)
    monkeypatch.setattr(epoch.bt, "Wallet", _Wallet)

    weights = await epoch.run_epoch(_settings(tmp_path), _SolvedProblemSource(), dry_run=False)

    assert weights == {1: 1.0}
    assert subtensor.set_weights_calls[0]["weights"] == [0.0, 1.0]


async def test_disk_preflight_skips_before_chain_query(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(epoch.shutil, "disk_usage", lambda path: SimpleNamespace(free=1))
    monkeypatch.setattr(epoch, "get_subtensor", lambda settings: (_ for _ in ()).throw(AssertionError("queried chain")))

    weights = await epoch.run_epoch(
        _settings(tmp_path, validator_min_free_bytes=2),
        _OneProblemSource(),
        dry_run=False,
    )

    assert weights == {}
