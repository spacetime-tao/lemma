"""Stable fingerprint for generated problem registry."""

from lemma.problems.generated import generated_registry_sha256


def test_generated_registry_sha256_stable() -> None:
    h = generated_registry_sha256()
    assert len(h) == 64
    assert generated_registry_sha256() == h
