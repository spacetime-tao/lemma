from lemma.common.config import LemmaSettings
from lemma.validator.service import epoch_sleep_seconds, validator_problem_window, validator_retry_sleep_seconds


def test_epoch_sleep_does_not_oversleep_near_boundary() -> None:
    assert epoch_sleep_seconds(29, 12.0) == 12.0


def test_epoch_sleep_polls_tightly_at_boundary() -> None:
    assert epoch_sleep_seconds(3, 12.0) == 1.0
    assert epoch_sleep_seconds(1, 12.0) == 0.0


def test_validator_retry_sleep_backs_off_rpc_429() -> None:
    assert validator_retry_sleep_seconds(RuntimeError("HTTP 429 too many requests"), 12.0) == 60.0


def test_validator_retry_sleep_keeps_generic_errors_short() -> None:
    assert validator_retry_sleep_seconds(RuntimeError("temporary failure"), 12.0) == 2.0


def test_validator_quantize_cadence_uses_problem_seed_window() -> None:
    settings = LemmaSettings().model_copy(
        update={
            "problem_seed_mode": "quantize",
            "problem_seed_quantize_blocks": 100,
            "netuid": 467,
        },
    )

    seed, blocks, edge = validator_problem_window(settings, object(), 7109268)

    assert seed == 7109200
    assert blocks == 32
    assert edge == "quantize_window"


def test_validator_subnet_epoch_cadence_preserves_epoch_window() -> None:
    class FakeSubtensor:
        def tempo(self, netuid: int, *, block: int) -> int:
            assert netuid == 467
            assert block == 7109268
            return 360

        def blocks_until_next_epoch(self, netuid: int) -> int:
            assert netuid == 467
            return 17

    settings = LemmaSettings().model_copy(
        update={
            "problem_seed_mode": "subnet_epoch",
            "netuid": 467,
        },
    )

    _, blocks, edge = validator_problem_window(settings, FakeSubtensor(), 7109268)

    assert blocks == 17
    assert edge == "subnet_epoch"
