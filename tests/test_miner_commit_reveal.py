"""Miner commit-reveal cache behavior."""

from __future__ import annotations

from lemma.common.config import LemmaSettings
from lemma.miner.forward import (
    CommitRevealCache,
    _commit_reveal_cache_key,
    make_forward,
)
from lemma.protocol import LemmaChallenge, ReasoningStep, synapse_miner_response_integrity_ok


class _Prover:
    async def solve(self, synapse: LemmaChallenge) -> tuple[str, str, list[ReasoningStep]]:
        return (
            "trace",
            "namespace Submission\n theorem t : True := by trivial\n",
            [ReasoningStep(title="Plan", text="Prove True directly.")],
        )


def _settings() -> LemmaSettings:
    return LemmaSettings(
        _env_file=None,
        miner_reject_past_deadline_block=False,
        miner_forward_summary=False,
        miner_forward_timeline=False,
        miner_log_forwards=False,
        miner_local_verify=False,
        miner_max_forwards_per_day=0,
    )


def _synapse(phase: str, validator_hotkey: str) -> LemmaChallenge:
    synapse = LemmaChallenge(
        theorem_id="gen/1",
        theorem_statement="theorem t : True := by sorry",
        lean_toolchain="lt",
        mathlib_rev="mr",
        deadline_unix=1,
        deadline_block=10,
        metronome_id="m1",
        commit_reveal_phase=phase,
    )
    synapse.dendrite.hotkey = validator_hotkey
    return synapse


def test_commit_reveal_cache_key_includes_validator_hotkey() -> None:
    a = _synapse("commit", "validator-a")
    b = _synapse("commit", "validator-b")

    assert _commit_reveal_cache_key(a) != _commit_reveal_cache_key(b)


def test_commit_reveal_cache_entry_expires() -> None:
    cache = CommitRevealCache(ttl_s=1.0)
    key = ("validator-a", "gen/1", "m1")

    cache.store(key, ("n", "proof", "trace", None), now=100.0)
    assert cache.pop(key, now=102.0) is None


async def test_miner_commit_reveal_cache_is_validator_bound() -> None:
    cache = CommitRevealCache()
    forward = make_forward(_settings(), _Prover(), commit_reveal_cache=cache)

    commit = await forward(_synapse("commit", "validator-a"))
    assert commit.proof_commitment_hex
    assert not commit.proof_script

    wrong_validator_reveal = await forward(_synapse("reveal", "validator-b"))
    assert wrong_validator_reveal.axon.status_code == 400
    assert "no cached commit" in (wrong_validator_reveal.axon.status_message or "")

    reveal = await forward(_synapse("reveal", "validator-a"))
    assert reveal.axon.status_code is None
    assert reveal.proof_script
    assert reveal.commit_reveal_nonce_hex
    assert synapse_miner_response_integrity_ok(reveal)


async def test_miner_response_sets_computed_body_hash() -> None:
    forward = make_forward(_settings(), _Prover())

    resp = await forward(_synapse("off", "validator-a"))

    assert resp.proof_script
    assert synapse_miner_response_integrity_ok(resp)


async def test_miner_commit_reveal_cache_is_forward_instance_scoped() -> None:
    commit_forward = make_forward(_settings(), _Prover(), commit_reveal_cache=CommitRevealCache())
    reveal_forward = make_forward(_settings(), _Prover(), commit_reveal_cache=CommitRevealCache())

    commit = await commit_forward(_synapse("commit", "validator-a"))
    assert commit.proof_commitment_hex

    reveal = await reveal_forward(_synapse("reveal", "validator-a"))
    assert reveal.axon.status_code == 400
    assert "no cached commit" in (reveal.axon.status_message or "")
