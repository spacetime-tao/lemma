"""Bittensor synapse: validator challenge and miner response."""

from __future__ import annotations

from typing import ClassVar

import bittensor as bt
from pydantic import BaseModel, ConfigDict, Field


class ReasoningStep(BaseModel):
    """One step in an informal solution narrative (PRM / process supervision)."""

    model_config = ConfigDict(extra="ignore")

    text: str = Field(..., description="Narrative content for this step.")
    title: str | None = Field(
        default=None,
        max_length=240,
        description="Optional short label (e.g. 'Factor the quadratic').",
    )


class LemmaChallenge(bt.Synapse):
    """
    Validator broadcasts a formal theorem; miner returns a reasoning trace and Lean proof.

    ``required_hash_fields`` drive :func:`bittensor.core.synapse.Synapse.body_hash`. That hash becomes
    ``computed_body_hash`` in HTTP headers on both the validator→miner request and the miner→validator response.
    Including miner-filled fields binds the **proof and reasoning** to the hash so a middle party cannot silently
    swap bytes after the miner signs (coordinated miner + validator release required when this list changes).
    """

    required_hash_fields: ClassVar[tuple[str, ...]] = (
        "theorem_id",
        "metronome_id",
        "theorem_statement",
        "lean_toolchain",
        "mathlib_rev",
        "deadline_block",
        "reasoning_trace",
        "reasoning_steps",
        "proof_script",
    )

    # --- Validator-filled (challenge) ---
    theorem_id: str = Field(
        ...,
        description="Stable problem identifier (e.g. miniF2F slug).",
    )
    theorem_statement: str = Field(
        ...,
        description="Full Lean 4 source the miner must close (often `theorem ... := by sorry`).",
    )
    imports: list[str] = Field(
        default_factory=lambda: ["Mathlib"],
        description="Suggested imports for the submission module.",
    )
    lean_toolchain: str = Field(
        ...,
        description="Pinned Lean release descriptor (e.g. leanprover/lean4:v4.15.0).",
    )
    mathlib_rev: str = Field(
        ...,
        description="mathlib4 git revision pinned for this round.",
    )
    deadline_unix: int = Field(
        ...,
        description="Unix time after which validators may ignore late responses.",
    )
    deadline_block: int | None = Field(
        default=None,
        description=(
            "First chain height where this challenge is treated as late — same cadence as the next problem-seed "
            "edge (Tempo epoch or quantize boundary)."
        ),
    )
    metronome_id: str = Field(
        ...,
        description="Unique id for this broadcast round (e.g. block hash snippet).",
    )

    # --- Miner-filled (response) ---
    reasoning_trace: str | None = Field(
        default=None,
        description=(
            "Flattened informal narrative — populated when routing structured steps to text for hashing/size; "
            "miners must supply reasoning_steps from the prover JSON (legacy reasoning_trace-only payloads fail)."
        ),
    )
    reasoning_steps: list[ReasoningStep] | None = Field(
        default=None,
        description="Structured informal reasoning (required from miner JSON); judge scores primarily from here.",
    )
    proof_script: str | None = Field(
        default=None,
        description="Full Lean 4 source for Submission.lean (namespace Submission, theorem name fixed).",
    )
    model_card: str | None = Field(
        default=None,
        description="Optional miner metadata: model id, revision, temperature.",
    )
    miner_verify_attest_signature_hex: str | None = Field(
        default=None,
        description=(
            "Optional Sr25519 signature (hex, 128 chars) over ``protocol_attest.miner_verify_attest_message`` "
            "when ``LEMMA_MINER_VERIFY_ATTEST_ENABLED=1``. Not part of ``body_hash``."
        ),
    )
    commit_reveal_phase: str = Field(
        default="off",
        description='Commit–reveal round: "off" (single phase), "commit" (hash only), or "reveal" (full proof + nonce).',
    )
    proof_commitment_hex: str | None = Field(
        default=None,
        description="SHA256 preimage commitment hex (64 chars), phase commit only; not in body_hash.",
    )
    commit_reveal_nonce_hex: str | None = Field(
        default=None,
        description="32-byte nonce as 64 hex chars; phase reveal only; not in body_hash.",
    )

    def deserialize(self) -> LemmaChallenge:
        """No-op: strings are already JSON-safe."""
        return self


def synapse_miner_response_integrity_ok(s: LemmaChallenge) -> bool:
    """Return True if recomputed :meth:`~bittensor.core.synapse.Synapse.body_hash` matches axon ``computed_body_hash``.

    When ``computed_body_hash`` is missing (older stacks / headers not merged), returns True so epochs keep working;
    when it is present and differs, the synapse body was altered after the miner built the response or the client is
    out of sync — drop the response.
    """
    expected = (s.computed_body_hash or "").strip()
    if not expected:
        return True
    return s.body_hash == expected
