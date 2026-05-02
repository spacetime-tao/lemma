from lemma.common.split_timeout import split_timeout_multiplier


def test_split_timeout_multiplier_defaults() -> None:
    assert split_timeout_multiplier("easy", 1.0, 2.0, 3.0) == 1.0
    assert split_timeout_multiplier("medium", 1.0, 2.0, 3.0) == 2.0
    assert split_timeout_multiplier("hard", 1.0, 2.0, 3.0) == 3.0
    assert split_timeout_multiplier("unknown", 1.0, 2.0, 3.0) == 1.0
