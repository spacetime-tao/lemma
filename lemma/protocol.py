"""Bittensor synapse for manual-proof WTA polling."""

from __future__ import annotations

from typing import ClassVar

import bittensor as bt
from pydantic import Field


class LemmaChallenge(bt.Synapse):
    """Validator polls for a proof of one locked target; miner may return ``proof_script``."""

    required_hash_fields: ClassVar[tuple[str, ...]] = (
        "theorem_id",
        "poll_id",
        "theorem_statement",
        "lean_toolchain",
        "mathlib_rev",
        "proof_script",
    )

    theorem_id: str = Field(..., description="Stable known-theorem target id.")
    theorem_statement: str = Field(..., description="Full trusted Challenge.lean source.")
    imports: list[str] = Field(default_factory=lambda: ["Mathlib"], description="Lean imports for the target.")
    lean_toolchain: str = Field(..., description="Pinned Lean release descriptor.")
    mathlib_rev: str = Field(..., description="Pinned Mathlib revision.")
    poll_id: str = Field(..., description="Validator-chosen id for this polling batch.")

    proof_script: str | None = Field(
        default=None,
        description="Full Lean source for Submission.lean when the miner has a matching stored proof.",
    )

    def deserialize(self) -> LemmaChallenge:
        return self


def synapse_miner_response_integrity_ok(s: LemmaChallenge) -> bool:
    """Reject explicit transport-hash mismatches when Bittensor exposes a hash."""
    expected = (s.computed_body_hash or "").strip()
    return not expected or s.body_hash == expected
