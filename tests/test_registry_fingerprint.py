"""Stable fingerprint for generated problem registry."""

from lemma.problems.generated import RNG_MIX_TAG, generated_registry_canonical_dict, generated_registry_sha256


def test_generated_registry_sha256_stable() -> None:
    h = generated_registry_sha256()
    assert len(h) == 64
    assert generated_registry_sha256() == h


def test_generated_registry_fingerprint_covers_source_and_rng_tag() -> None:
    registry = generated_registry_canonical_dict()
    builders = registry["builders"]

    assert registry["rng_mix_tag"] == RNG_MIX_TAG
    assert registry["builder_count"] == 40
    assert registry["split_counts"] == {"easy": 10, "medium": 22, "hard": 8}
    assert len(builders) == 40
    assert all(len(builder["source_sha256"]) == 64 for builder in builders)
