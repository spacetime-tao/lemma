"""Weight vector construction for set_weights."""

from lemma.validator.weights_policy import build_full_weights


def test_build_full_weights_normalizes() -> None:
    full, skip = build_full_weights(4, {1: 0.5, 2: 0.5}, empty_policy="skip")
    assert not skip
    assert len(full) == 4
    assert abs(sum(full) - 1.0) < 1e-6
    assert full[0] == 0.0 and full[3] == 0.0


def test_empty_skip() -> None:
    full, skip = build_full_weights(3, {}, empty_policy="skip")
    assert skip
    assert full == [0.0, 0.0, 0.0]


def test_empty_uniform() -> None:
    full, skip = build_full_weights(3, {}, empty_policy="uniform")
    assert not skip
    assert all(abs(x - 1 / 3) < 1e-9 for x in full)


def test_empty_uniform_excludes_validator_uid() -> None:
    full, skip = build_full_weights(4, {}, empty_policy="uniform", exclude_uid=2)
    assert not skip
    assert full[2] == 0.0
    assert abs(sum(full) - 1.0) < 1e-9
    for i in (0, 1, 3):
        assert abs(full[i] - 1.0 / 3.0) < 1e-9
