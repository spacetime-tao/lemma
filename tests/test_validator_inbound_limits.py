from __future__ import annotations

from types import SimpleNamespace

from lemma.common.config import LemmaSettings
from lemma.lean.sandbox import VerifyResult
from lemma.problems.base import Problem, ProblemSource
from lemma.protocol import LemmaChallenge
from lemma.validator import epoch


class _OneProblemSource(ProblemSource):
    def __init__(self) -> None:
        self.problem = Problem(
            id="known/test/one",
            theorem_name="t",
            type_expr="True",
            split="wta",
            lean_toolchain="lt",
            mathlib_rev="mr",
            imports=("Mathlib",),
        )

    def all_problems(self) -> list[Problem]:
        return [self.problem]

    def sample(self, seed: int, split: str | None = None) -> Problem:
        return self.problem

    def get(self, problem_id: str) -> Problem:
        if problem_id != self.problem.id:
            raise KeyError(problem_id)
        return self.problem


class _Subtensor:
    def get_current_block(self) -> int:
        return 50

    def metagraph(self, netuid: int) -> SimpleNamespace:
        return SimpleNamespace(n=1, axons=[object()])

    def get_uid_for_hotkey_on_subnet(self, hotkey: str, netuid: int) -> None:
        return None


class _Dendrite:
    def __init__(self, *, wallet: object) -> None:
        self.wallet = wallet

    async def __aenter__(self) -> _Dendrite:
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
            poll_id=synapse.poll_id,
            proof_script="x" * 1025,
        )
        resp.dendrite.status_code = 200
        resp.dendrite.status_message = "Success"
        return [resp]


class _Wallet:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.hotkey = SimpleNamespace(ss58_address="validator-hotkey")


async def test_validator_rejects_oversized_proof_before_lean(monkeypatch, tmp_path) -> None:
    verify_calls: list[str] = []

    def fake_run_lean_verify(*args: object, **kwargs: object) -> VerifyResult:
        verify_calls.append(str(kwargs["proof_script"]))
        return VerifyResult(passed=True, reason="ok")

    monkeypatch.setattr(epoch, "get_subtensor", lambda settings: _Subtensor())
    monkeypatch.setattr(epoch.bt, "Wallet", _Wallet)
    monkeypatch.setattr(epoch.bt, "Dendrite", _Dendrite)
    monkeypatch.setattr(epoch, "run_lean_verify", fake_run_lean_verify)

    settings = LemmaSettings(
        _env_file=None,
        synapse_max_proof_chars=1024,
        wta_ledger_path=tmp_path / "wta-ledger.jsonl",
        validator_abort_if_not_registered=False,
        validator_min_free_bytes=0,
    )

    weights = await epoch.run_epoch(settings, _OneProblemSource(), dry_run=True)

    assert weights == {}
    assert verify_calls == []
