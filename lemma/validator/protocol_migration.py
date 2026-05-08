"""Gated protocol / incentive features not yet fully wired (hard-migration hooks).

See ``docs/incentive_migration.md`` for design. Environment flags default to **off**; turning on an
unimplemented feature fails fast at validator startup (except implemented attest modes).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lemma.common.config import LemmaSettings


def validate_protocol_feature_flags(settings: LemmaSettings) -> None:
    """Raise ``SystemExit`` if an unsupported protocol flag is enabled."""
    if settings.lemma_commit_reveal_enabled:
        raise SystemExit(
            "LEMMA_COMMIT_REVEAL_ENABLED=1 is not implemented yet.\n"
            "See docs/incentive_migration.md — disable the flag or use an older release.",
        )
    if settings.lemma_judge_profile_attest_enabled:
        raise SystemExit(
            "LEMMA_JUDGE_PROFILE_ATTEST_ENABLED=1 is not implemented yet.\n"
            "See docs/incentive_migration.md — disable the flag or use an older release.",
        )
