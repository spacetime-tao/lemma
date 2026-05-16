"""Construct the active :class:`~lemma.problems.base.ProblemSource` from settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lemma.problems.base import Problem, ProblemSource
from lemma.problems.generated import GeneratedProblemSource
from lemma.problems.hybrid import CuratedCatalogSource, HybridProblemSource
from lemma.problems.minif2f import MiniF2FSource

if TYPE_CHECKING:
    from lemma.common.config import LemmaSettings


def get_problem_source(settings: LemmaSettings) -> ProblemSource:
    """Return hybrid default, generated-only rollback, or gated frozen backend."""
    mode = (settings.problem_source or "hybrid").strip().lower()
    if mode == "hybrid":
        return HybridProblemSource(
            generated=GeneratedProblemSource(legacy_plain_rng=settings.lemma_generated_legacy_plain_rng),
            generated_weight=settings.lemma_hybrid_generated_weight,
            catalog_weight=settings.lemma_hybrid_catalog_weight,
        )
    if mode == "frozen":
        if not settings.lemma_dev_allow_frozen_problem_source:
            raise ValueError(
                "LEMMA_PROBLEM_SOURCE=frozen is disabled by default (public miniF2F-style catalog). "
                "Use LEMMA_PROBLEM_SOURCE=hybrid for subnet traffic, or set "
                "LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1 for local benchmarking only "
                "(see docs/catalog-sources.md).",
            )
        return MiniF2FSource(settings.minif2f_catalog_path)
    if mode != "generated":
        raise ValueError(f"Unknown LEMMA_PROBLEM_SOURCE={settings.problem_source!r}")
    return GeneratedProblemSource(legacy_plain_rng=settings.lemma_generated_legacy_plain_rng)


def resolve_problem(settings: LemmaSettings, problem_id: str) -> Problem:
    """Resolve ``gen/<int>`` via generation; otherwise load gated frozen catalog."""
    if problem_id.startswith("gen/"):
        return GeneratedProblemSource(
            legacy_plain_rng=settings.lemma_generated_legacy_plain_rng,
        ).get(problem_id)
    if problem_id.startswith("curated/"):
        return CuratedCatalogSource().get(problem_id)
    if not settings.lemma_dev_allow_frozen_problem_source:
        raise ValueError(
            "Frozen catalog problem ids are disabled by default (public miniF2F-style catalog). "
            "Use gen/<seed> or curated/<id> ids for subnet traffic, or set LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1 "
            "for local benchmarking only (see docs/catalog-sources.md).",
        )
    return MiniF2FSource(settings.minif2f_catalog_path).get(problem_id)
