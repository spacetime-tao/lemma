"""Problem source factory — frozen catalog gating."""

from lemma.common.config import LemmaSettings
from lemma.problems.factory import get_problem_source


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


def test_generated_default() -> None:
    s = LemmaSettings()
    src = get_problem_source(s)
    assert src is not None
