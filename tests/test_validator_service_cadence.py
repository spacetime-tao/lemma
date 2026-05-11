from lemma.validator.service import epoch_sleep_seconds


def test_epoch_sleep_does_not_oversleep_near_boundary() -> None:
    assert epoch_sleep_seconds(29, 12.0) == 12.0


def test_epoch_sleep_polls_tightly_at_boundary() -> None:
    assert epoch_sleep_seconds(3, 12.0) == 1.0
    assert epoch_sleep_seconds(1, 12.0) == 0.0
