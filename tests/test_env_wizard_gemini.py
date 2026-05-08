"""Sanity checks for Gemini prover presets in env_wizard."""

from lemma.cli.env_wizard import _GEMINI_PRESET_ROWS, GEMINI_OPENAI_BASE_URL


def test_gemini_openai_base_url_is_google_openai_compat() -> None:
    assert GEMINI_OPENAI_BASE_URL.startswith("https://generativelanguage.googleapis.com/")
    assert GEMINI_OPENAI_BASE_URL.rstrip("/").endswith("openai")


def test_gemini_preset_menu_unique_numbers_and_models() -> None:
    nums = [r[0] for r in _GEMINI_PRESET_ROWS]
    models = [r[1] for r in _GEMINI_PRESET_ROWS]
    assert len(nums) == len(set(nums))
    assert len(models) == len(set(models))
    assert set(nums) == {"1", "2", "3"}
    assert any("gemini-pro-latest" in m for m in models)
    assert any("gemini-flash-latest" in m for m in models)
    assert any("gemini-flash-lite-latest" in m for m in models)
