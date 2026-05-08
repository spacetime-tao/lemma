"""Gated protocol / incentive features (hard-migration hooks).

See ``docs/incentive_migration.md`` for design. Environment flags default to **off**; turning on an
unimplemented feature should fail fast at validator startup (see ``validate_protocol_feature_flags``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lemma.common.config import LemmaSettings


def validate_protocol_feature_flags(_settings: LemmaSettings) -> None:
    """Raise ``SystemExit`` if an unsupported protocol flag is enabled."""
    pass
