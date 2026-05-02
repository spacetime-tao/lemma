"""LLM-as-judge for reasoning traces."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field


class RubricScore(BaseModel):
    coherence: float = Field(ge=0.0, le=1.0)
    exploration: float = Field(ge=0.0, le=1.0)
    clarity: float = Field(ge=0.0, le=1.0)
    composite: float = Field(ge=0.0, le=1.0)


class Judge(Protocol):
    async def score(self, theorem: str, trace: str, proof: str) -> RubricScore:
        """Return rubric scores for a reasoning trace and Lean proof."""
