from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from lemma.common.config import LemmaSettings
from lemma.lean.sandbox import VerifyResult
from lemma.problems.base import Problem, ProblemSource
from lemma.protocol import LemmaChallenge
from lemma.validator import epoch


class _OneProblemSource(ProblemSource):
    problem = Problem(
        id="gen/1",
        theorem_name="t",
        type_expr="True",
        split="easy",
        lean_toolchain="lt",
        mathlib_rev="mr",
        imports=("Mathlib",),
    )

    def all_problems(self) -> list[Problem]:
        return [self.problem]

    def sample(self, seed: int, split: str | None = None) -> Problem:
        return self.problem


class _Subtensor:
    def __init__(self) -> None:
        self.set_weights_calls: list[dict[str, Any]] = []

    def get_current_block(self) -> int:
        return 50

    def metagraph(self, netuid: int) -> SimpleNamespace:
        return SimpleNamespace(
            n=1,
            axons=[object()],
            hotkeys=["miner-hotkey"],
            coldkeys=["miner-coldkey"],
        )

    def get_uid_for_hotkey_on_subnet(self, hotkey: str, netuid: int) -> None:
        return None

    def set_weights(self, **kwargs: Any) -> SimpleNamespace:
        self.set_weights_calls.append(kwargs)
        return SimpleNamespace(success=True, message="ok")


class _SequencedSubtensor(_Subtensor):
    def __init__(self, results: list[object]) -> None:
        super().__init__()
        self.results = results

    def set_weights(self, **kwargs: Any) -> object:
        self.set_weights_calls.append(kwargs)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class _Wallet:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.hotkey = SimpleNamespace(ss58_address="validator-hotkey")


def _settings(tmp_path, **updates: object) -> LemmaSettings:
    base = {
        "_env_file": None,
        "lemma_reputation_state_path": tmp_path / "reputation.json",
        "validator_min_free_bytes": 0,
    }
    base.update(updates)
    return LemmaSettings(**base)


def _install_epoch_fakes(
    monkeypatch,
    *,
    subtensor: _Subtensor,
    verify_result: VerifyResult,
    proof_script: str = "namespace Submission\n",
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
        ) -> list[LemmaChallenge]:
            resp = LemmaChallenge(
                theorem_id=synapse.theorem_id,
                theorem_statement=synapse.theorem_statement,
                imports=list(synapse.imports or []),
                lean_toolchain=synapse.lean_toolchain,
                mathlib_rev=synapse.mathlib_rev,
                deadline_unix=synapse.deadline_unix,
                deadline_block=synapse.deadline_block,
                metronome_id=synapse.metronome_id,
                proof_script=proof_script,
            )
            resp.dendrite.status_code = 200
            resp.dendrite.status_message = "Success"
            return [resp]

    def run_lean_verify(*args: object, **kwargs: object) -> VerifyResult:
        return verify_result

    monkeypatch.setattr(epoch, "get_subtensor", lambda settings: subtensor)
    monkeypatch.setattr(epoch.bt, "Wallet", _Wallet)
    monkeypatch.setattr(epoch.bt, "Dendrite", Dendrite)
    monkeypatch.setattr(epoch, "run_lean_verify", run_lean_verify)


def test_set_weights_outcome_handles_bittensor_shapes() -> None:
    assert epoch._set_weights_outcome((False, "rate limited")) == (False, "rate limited")
    assert epoch._set_weights_outcome((True, "ok")) == (True, "ok")
    assert epoch._set_weights_outcome(False) == (False, "False")

    ok, message = epoch._set_weights_outcome(SimpleNamespace(success=False, message=None))
    assert not ok
    assert "success=False" in message


async def test_training_export_oserror_does_not_block_set_weights(monkeypatch, tmp_path) -> None:
    subtensor = _Subtensor()
    _install_epoch_fakes(
        monkeypatch,
        subtensor=subtensor,
        verify_result=VerifyResult(passed=True, reason="ok"),
    )

    def fail_append(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(epoch, "append_epoch_jsonl", fail_append)

    weights = await epoch.run_epoch(
        _settings(tmp_path, training_export_jsonl=tmp_path / "export.jsonl"),
        _OneProblemSource(),
        dry_run=False,
    )

    assert weights == {0: 1.0}
    assert len(subtensor.set_weights_calls) == 1


async def test_set_weights_tuple_failure_retries_until_success(monkeypatch, tmp_path) -> None:
    subtensor = _SequencedSubtensor([(False, "rate limited"), (True, "ok")])
    _install_epoch_fakes(
        monkeypatch,
        subtensor=subtensor,
        verify_result=VerifyResult(passed=True, reason="ok"),
    )

    async def no_sleep(delay: float) -> None:
        return None

    monkeypatch.setattr(epoch.asyncio, "sleep", no_sleep)

    weights = await epoch.run_epoch(
        _settings(tmp_path, set_weights_max_retries=2),
        _OneProblemSource(),
        dry_run=False,
    )

    assert weights == {0: 1.0}
    assert len(subtensor.set_weights_calls) == 2


async def test_set_weights_exception_retries_until_success(monkeypatch, tmp_path) -> None:
    subtensor = _SequencedSubtensor([RuntimeError("rpc down"), SimpleNamespace(success=True, message="ok")])
    _install_epoch_fakes(
        monkeypatch,
        subtensor=subtensor,
        verify_result=VerifyResult(passed=True, reason="ok"),
    )

    async def no_sleep(delay: float) -> None:
        return None

    monkeypatch.setattr(epoch.asyncio, "sleep", no_sleep)

    weights = await epoch.run_epoch(
        _settings(tmp_path, set_weights_max_retries=2),
        _OneProblemSource(),
        dry_run=False,
    )

    assert weights == {0: 1.0}
    assert len(subtensor.set_weights_calls) == 2


async def test_disk_preflight_skips_before_dendrite_or_subtensor(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        epoch.shutil,
        "disk_usage",
        lambda path: SimpleNamespace(free=1),
    )
    monkeypatch.setattr(epoch, "get_subtensor", lambda settings: (_ for _ in ()).throw(AssertionError("queried chain")))

    weights = await epoch.run_epoch(
        _settings(tmp_path, validator_min_free_bytes=2),
        _OneProblemSource(),
        dry_run=False,
    )

    assert weights == {}


async def test_verify_infra_failure_is_exported_and_not_counted_for_credibility(monkeypatch, tmp_path) -> None:
    subtensor = _Subtensor()
    _install_epoch_fakes(
        monkeypatch,
        subtensor=subtensor,
        verify_result=VerifyResult(passed=False, reason="docker_error", stderr_tail="docker unavailable"),
    )
    credibility_candidates: list[list[tuple[int, LemmaChallenge]]] = []

    def capture_credibility(cstore, candidates, verified, *, alpha: float) -> None:
        credibility_candidates.append(list(candidates))

    monkeypatch.setattr(epoch, "_update_verify_credibility", capture_credibility)
    export_path = tmp_path / "export.jsonl"

    weights = await epoch.run_epoch(
        _settings(
            tmp_path,
            training_export_jsonl=export_path,
            lemma_reputation_verify_credibility_alpha=1.0,
        ),
        _OneProblemSource(),
        dry_run=False,
    )

    rows = [json.loads(line) for line in export_path.read_text(encoding="utf-8").splitlines()]
    assert weights == {}
    assert rows[-1]["record_type"] == "round_summary"
    assert rows[-1]["verify_infra_error_uids"] == [0]
    assert credibility_candidates == [[]]
    assert subtensor.set_weights_calls == []


async def test_all_fail_epoch_persists_verify_credibility_downgrade(monkeypatch, tmp_path) -> None:
    subtensor = _Subtensor()
    _install_epoch_fakes(
        monkeypatch,
        subtensor=subtensor,
        verify_result=VerifyResult(passed=False, reason="compile_error", stderr_tail="bad proof"),
    )
    reputation_path = tmp_path / "reputation.json"

    weights = await epoch.run_epoch(
        _settings(
            tmp_path,
            lemma_reputation_state_path=reputation_path,
            lemma_reputation_verify_credibility_alpha=1.0,
        ),
        _OneProblemSource(),
        dry_run=False,
    )

    state = json.loads(reputation_path.read_text(encoding="utf-8"))
    assert weights == {}
    assert state["credibility_by_uid"] == {"0": 0.0}
    assert subtensor.set_weights_calls == []
