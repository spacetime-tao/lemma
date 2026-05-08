"""Deterministic generated problem source."""

from lemma.problems.generated import GeneratedProblemSource, expand_seed_for_problem_rng


def test_expand_seed_deterministic() -> None:
    assert expand_seed_for_problem_rng(42) == expand_seed_for_problem_rng(42)
    assert expand_seed_for_problem_rng(42) != expand_seed_for_problem_rng(43)


def test_mix_changes_template_vs_legacy_sometimes() -> None:
    old = GeneratedProblemSource(legacy_plain_rng=True)
    new = GeneratedProblemSource(legacy_plain_rng=False)
    diffs = 0
    for s in range(5000):
        if old.sample(s).extra.get("builder_index") != new.sample(s).extra.get("builder_index"):
            diffs += 1
    assert diffs > 0, "expected SHA256-mixed RNG to change some template picks vs legacy"


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


def test_legacy_plain_rng_opt_in() -> None:
    """Rollback path: legacy matches historical Random(seed) mapping."""
    plain = GeneratedProblemSource(legacy_plain_rng=True)
    a = plain.sample(100)
    b = GeneratedProblemSource(legacy_plain_rng=True).sample(100)
    assert a.challenge_source() == b.challenge_source()
