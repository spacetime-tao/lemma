"""
Minimal patterns for interacting with Lemma off-chain.

Uses the same synapse schema the subnet expects; wire `bt.Dendrite` when you have
a live metagraph and axon endpoints.
"""

from lemma.protocol import LemmaChallenge

# Example challenge (normally built by the validator from `MiniF2FSource`).
synapse = LemmaChallenge(
    theorem_id="demo/two_plus_two",
    theorem_statement="import Mathlib\n\ntheorem two_plus_two_eq_four : (2 : Nat) + 2 = 4 := by sorry\n",
    imports=["Mathlib"],
    lean_toolchain="leanprover/lean4:v4.30.0-rc2",
    mathlib_rev="5450b53e5ddc",
    deadline_unix=0,
    metronome_id="example",
    timeout=120.0,
)

# Miner fills these fields before returning the synapse:
synapse.reasoning_trace = "Use rfl: 2+2 reduces to 4."
synapse.proof_script = """import Mathlib

namespace Submission

theorem two_plus_two_eq_four : (2 : Nat) + 2 = 4 := by rfl

end Submission
"""

print(synapse.model_dump_json(indent=2))
