"""Optional comparator hook."""

import os

from lemma.lean.comparator_hook import ComparatorHookResult, hook_failure_reason, run_comparator_hook


def test_comparator_skipped_by_default(tmp_path) -> None:
    os.environ.pop("LEMMA_COMPARATOR_ENABLED", None)
    os.environ.pop("LEMMA_COMPARATOR_CMD", None)
    assert run_comparator_hook(tmp_path, timeout_s=5.0) is None


def test_hook_failure_reason() -> None:
    assert hook_failure_reason(None) is None
    assert hook_failure_reason(ComparatorHookResult(ok=True)) is None
    assert hook_failure_reason(ComparatorHookResult(ok=False, stderr_tail="no")) == "comparator_rejected"
