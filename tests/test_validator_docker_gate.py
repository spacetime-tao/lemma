"""Validator refuses host Lean without explicit acknowledgement."""

import pytest
from lemma.common.config import LemmaSettings
from lemma.validator.service import _require_docker_for_validator


def test_validator_requires_docker_by_default() -> None:
    s = LemmaSettings().model_copy(update={"lean_use_docker": False})
    with pytest.raises(SystemExit, match="requires Docker"):
        _require_docker_for_validator(s)


def test_validator_ok_when_docker_on() -> None:
    s = LemmaSettings().model_copy(update={"lean_use_docker": True})
    _require_docker_for_validator(s)
