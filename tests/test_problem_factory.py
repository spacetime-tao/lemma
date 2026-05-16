"""Problem source factory — frozen catalog gating."""

from lemma.common.config import LemmaSettings
from lemma.problems.factory import get_problem_source, resolve_problem
from lemma.problems.hybrid import CuratedCatalogSource, HybridProblemSource
from lemma.problems.minif2f import MiniF2FSource


def test_frozen_requires_dev_flag() -> None:
    s = LemmaSettings(problem_source="frozen")
    try:
        get_problem_source(s)
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "LEMMA_DEV_ALLOW_FROZEN" in str(e)


def test_frozen_allowed_with_dev_flag() -> None:
    s = LemmaSettings(problem_source="frozen", lemma_dev_allow_frozen_problem_source=True)
    src = get_problem_source(s)
    assert src is not None


def test_hybrid_default() -> None:
    s = LemmaSettings()
    src = get_problem_source(s)
    assert isinstance(src, HybridProblemSource)


def test_resolve_generated_id_does_not_need_frozen_dev_flag() -> None:
    s = LemmaSettings(lemma_dev_allow_frozen_problem_source=False)
    p = resolve_problem(s, "gen/42")
    assert p.id == "gen/42"


def test_resolve_curated_id_does_not_need_frozen_dev_flag() -> None:
    curated_id = CuratedCatalogSource().all_problems()[0].id
    s = LemmaSettings(lemma_dev_allow_frozen_problem_source=False)
    p = resolve_problem(s, curated_id)
    assert p.id == curated_id


def test_resolve_frozen_id_requires_dev_flag() -> None:
    s = LemmaSettings(lemma_dev_allow_frozen_problem_source=False)
    try:
        resolve_problem(s, "mini/demo")
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "LEMMA_DEV_ALLOW_FROZEN" in str(e)


def test_resolve_frozen_id_allowed_with_dev_flag() -> None:
    frozen_id = MiniF2FSource().all_problems()[0].id
    s = LemmaSettings(lemma_dev_allow_frozen_problem_source=True)
    p = resolve_problem(s, frozen_id)
    assert p.id == frozen_id
