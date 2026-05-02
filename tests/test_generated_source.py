"""Deterministic generated problem source."""

from lemma.problems.generated import GeneratedProblemSource


def test_sample_stable_across_calls() -> None:
    src = GeneratedProblemSource()
    a = src.sample(42)
    b = src.sample(42)
    assert a.id == b.id == "gen/42"
    assert a.theorem_name == b.theorem_name
    assert a.challenge_source() == b.challenge_source()
    assert isinstance(a.extra.get("builder_index"), int)
    assert a.extra.get("template_fn", "").startswith("_b_")


def test_get_matches_sample() -> None:
    src = GeneratedProblemSource()
    p = src.get("gen/42")
    assert p == src.sample(42)


def test_different_seeds_usually_differ() -> None:
    src = GeneratedProblemSource()
    p1 = src.sample(41)
    p2 = src.sample(42)
    assert p1.id != p2.id


def test_split_filters_only_easy_or_medium_or_hard() -> None:
    src = GeneratedProblemSource()
    for spl in ("easy", "medium", "hard"):
        p = src.sample(99991, split=spl)
        assert p.split == spl
