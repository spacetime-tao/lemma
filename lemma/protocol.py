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

    ``required_hash_fields`` binds the body hash to the specific challenge instance.
    """

    required_hash_fields: ClassVar[tuple[str, ...]] = (
        "theorem_id",
        "metronome_id",
        "theorem_statement",
        "lean_toolchain",
        "mathlib_rev",
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
    metronome_id: str = Field(
        ...,
        description="Unique id for this broadcast round (e.g. block hash snippet).",
    )

    # --- Miner-filled (response) ---
    reasoning_trace: str | None = Field(
        default=None,
        description="Flat step-by-step reasoning (legacy); prefer reasoning_steps when possible.",
    )
    reasoning_steps: list[ReasoningStep] | None = Field(
        default=None,
        description="Structured PRM-style steps; judge prefers this over reasoning_trace when set.",
    )
    proof_script: str | None = Field(
        default=None,
        description="Full Lean 4 source for Submission.lean (namespace Submission, theorem name fixed).",
    )
    model_card: str | None = Field(
        default=None,
        description="Optional miner metadata: model id, revision, temperature.",
    )

    def deserialize(self) -> LemmaChallenge:
        """No-op: strings are already JSON-safe."""
        return self
