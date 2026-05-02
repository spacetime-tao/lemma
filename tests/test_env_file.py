from pathlib import Path

from lemma.common.env_file import merge_dotenv


def test_merge_dotenv_updates_keys(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_text("FOO=1\n# c\nBAR=two\n", encoding="utf-8")
    merge_dotenv(p, {"BAR": "new", "BAZ": " three "})
    text = p.read_text(encoding="utf-8")
    assert "FOO=1" in text
    assert 'BAR="new"' in text
    assert 'BAZ=" three "' in text
    assert "two" not in text
