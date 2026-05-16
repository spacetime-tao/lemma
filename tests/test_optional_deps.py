import builtins

import pytest
from lemma.common.async_llm_retry import require_anthropic_sdk


def test_missing_anthropic_extra_has_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name == "anthropic":
            raise ImportError("blocked")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)

    with pytest.raises(RuntimeError, match="uv sync --extra anthropic"):
        require_anthropic_sdk()
