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


class _TwoMinerSubtensor(_Subtensor):
    def metagraph(self, netuid: int) -> SimpleNamespace:
        return SimpleNamespace(
            n=2,
            axons=[SimpleNamespace(uid=0), SimpleNamespace(uid=1)],
            hotkeys=["miner-hotkey-0", "miner-hotkey-1"],
            coldkeys=["miner-coldkey-0", "miner-coldkey-1"],
        )


class _ThreeMinerSubtensor(_Subtensor):
    def metagraph(self, netuid: int) -> SimpleNamespace:
        return SimpleNamespace(
            n=3,
            axons=[SimpleNamespace(uid=0), SimpleNamespace(uid=1), SimpleNamespace(uid=2)],
            hotkeys=["miner-hotkey-0", "miner-hotkey-1", "validator-hotkey"],
            coldkeys=["miner-coldkey-0", "miner-coldkey-1", "validator-coldkey"],
        )

    def get_uid_for_hotkey_on_subnet(self, hotkey: str, netuid: int) -> int | None:
        return 2 if hotkey == "validator-hotkey" else None


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
    assert epoch._set_weights_outcome((False, None)) == (False, "success=False without message")
    assert epoch._set_weights_outcome({"success": False}) == (False, "success=False without message")
    assert epoch._set_weights_outcome(False) == (False, "False")

    ok, message = epoch._set_weights_outcome(SimpleNamespace(success=False, message=None))
    assert not ok
    assert message == "success=False without message"


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
    assert subtensor.set_weights_calls == []


async def test_no_positive_rolling_scores_skips_set_weights(monkeypatch, tmp_path) -> None:
    subtensor = _Subtensor()
    _install_epoch_fakes(
        monkeypatch,
        subtensor=subtensor,
        verify_result=VerifyResult(passed=False, reason="compile_error"),
    )

    weights = await epoch.run_epoch(
        _settings(tmp_path, empty_epoch_weights_policy="uniform"),
        _OneProblemSource(),
        dry_run=False,
    )

    assert weights == {}
    assert subtensor.set_weights_calls == []


async def test_epoch_updates_rolling_score_for_all_queried_uids(monkeypatch, tmp_path) -> None:
    subtensor = _TwoMinerSubtensor()

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
            out = []
            for axon in axons:
                uid = int(axon.uid)
                proof = "namespace Submission\n" if uid == 0 else ""
                resp = LemmaChallenge(
                    theorem_id=synapse.theorem_id,
                    theorem_statement=synapse.theorem_statement,
                    imports=list(synapse.imports or []),
                    lean_toolchain=synapse.lean_toolchain,
                    mathlib_rev=synapse.mathlib_rev,
                    deadline_unix=synapse.deadline_unix,
                    deadline_block=synapse.deadline_block,
                    metronome_id=synapse.metronome_id,
                    proof_script=proof,
                )
                resp.dendrite.status_code = 200
                resp.dendrite.status_message = "Success"
                out.append(resp)
            return out

    monkeypatch.setattr(epoch, "get_subtensor", lambda settings: subtensor)
    monkeypatch.setattr(epoch.bt, "Wallet", _Wallet)
    monkeypatch.setattr(epoch.bt, "Dendrite", Dendrite)
    monkeypatch.setattr(epoch, "run_lean_verify", lambda *args, **kwargs: VerifyResult(passed=True, reason="ok"))

    weights = await epoch.run_epoch(
        _settings(tmp_path, lemma_scoring_rolling_alpha=0.5),
        _OneProblemSource(),
        dry_run=False,
    )
    state = json.loads((tmp_path / "reputation.json").read_text(encoding="utf-8"))

    assert weights == {0: 1.0}
    assert state["rolling_score_by_uid"] == {"0": 0.5, "1": 0.0}


async def test_epoch_weights_ignore_stale_and_validator_rolling_scores(monkeypatch, tmp_path) -> None:
    reputation_path = tmp_path / "reputation.json"
    reputation_path.write_text(
        json.dumps(
            {
                "version": 3,
                "rolling_score_by_uid": {"0": 0.5, "1": 0.5, "2": 1.0, "99": 1.0},
                "ema_by_uid": {},
                "credibility_by_uid": {},
            },
        ),
        encoding="utf-8",
    )
    subtensor = _ThreeMinerSubtensor()

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
            return [object() for _axon in axons]

    monkeypatch.setattr(epoch, "get_subtensor", lambda settings: subtensor)
    monkeypatch.setattr(epoch.bt, "Wallet", _Wallet)
    monkeypatch.setattr(epoch.bt, "Dendrite", Dendrite)

    weights = await epoch.run_epoch(
        _settings(
            tmp_path,
            lemma_reputation_state_path=reputation_path,
            lemma_scoring_rolling_alpha=0.0,
        ),
        _OneProblemSource(),
        dry_run=False,
    )

    assert weights == {0: 0.5, 1: 0.5}
    assert subtensor.set_weights_calls[0]["weights"] == [0.5, 0.5, 0.0]


def test_uid_variant_problem_sampling_uses_same_split() -> None:
    class Source(_OneProblemSource):
        def sample(self, seed: int, split: str | None = None) -> Problem:
            return Problem(
                id=f"gen/{seed}",
                theorem_name=f"t_{seed}",
                type_expr=f"{seed} = {seed}",
                split=split or "hard",
                lean_toolchain="lt",
                mathlib_rev="mr",
                imports=("Mathlib",),
            )

    source = Source()
    anchor = source.sample(seed=100)
    problems = {
        uid: source.sample(seed=epoch._uid_variant_seed(100, uid), split=anchor.split) for uid in (1, 2)
    }

    assert problems[1].split == problems[2].split == "hard"
    assert problems[1].challenge_source() != problems[2].challenge_source()


async def test_uid_variant_epoch_binds_distinct_challenges_per_uid(monkeypatch, tmp_path) -> None:
    subtensor = _TwoMinerSubtensor()
    seen: list[tuple[int, LemmaChallenge]] = []

    class Source(_OneProblemSource):
        def sample(self, seed: int, split: str | None = None) -> Problem:
            split_key = split or "hard"
            return Problem(
                id=f"gen/{seed}",
                theorem_name=f"t_{seed}",
                type_expr=f"{seed} = {seed}",
                split=split_key,
                lean_toolchain="lt",
                mathlib_rev="mr",
                imports=("Mathlib",),
            )

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
            uid = int(axons[0].uid)
            seen.append((uid, synapse))
            resp = LemmaChallenge(
                theorem_id=synapse.theorem_id,
                theorem_statement=synapse.theorem_statement,
                imports=list(synapse.imports or []),
                lean_toolchain=synapse.lean_toolchain,
                mathlib_rev=synapse.mathlib_rev,
                deadline_unix=synapse.deadline_unix,
                deadline_block=synapse.deadline_block,
                metronome_id=synapse.metronome_id,
                proof_script="namespace Submission\n",
            )
            resp.dendrite.status_code = 200
            resp.dendrite.status_message = "Success"
            return [resp]

    monkeypatch.setattr(epoch, "get_subtensor", lambda settings: subtensor)
    monkeypatch.setattr(epoch.bt, "Wallet", _Wallet)
    monkeypatch.setattr(epoch.bt, "Dendrite", Dendrite)
    monkeypatch.setattr(epoch, "run_lean_verify", lambda *args, **kwargs: VerifyResult(passed=True, reason="ok"))

    weights = await epoch.run_epoch(
        _settings(
            tmp_path,
            lemma_uid_variant_problems=True,
            lemma_scoring_rolling_alpha=1.0,
        ),
        Source(),
        dry_run=False,
    )

    by_uid = {uid: synapse for uid, synapse in seen}
    assert weights == {0: 0.5, 1: 0.5}
    assert set(by_uid) == {0, 1}
    assert by_uid[0].theorem_id != by_uid[1].theorem_id
    assert by_uid[0].theorem_statement != by_uid[1].theorem_statement
    assert by_uid[0].metronome_id.endswith(":0")
    assert by_uid[1].metronome_id.endswith(":1")


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
