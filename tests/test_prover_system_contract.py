"""Built-in prover system prompt is the single miner LLM contract (no env append)."""

from lemma.miner.prover import PROVER_SYSTEM


def test_prover_system_contract_nonempty():
    assert "reasoning_steps" in PROVER_SYSTEM
    assert "proof_script" in PROVER_SYSTEM
    assert PROVER_SYSTEM.startswith("You are an expert Lean 4 prover")
    assert "namespace Submission" in PROVER_SYSTEM
    assert "Solution.lean" in PROVER_SYSTEM
    assert "abs_add_le" in PROVER_SYSTEM
    assert "formal goal" in PROVER_SYSTEM.lower() or "theorem as stated" in PROVER_SYSTEM
