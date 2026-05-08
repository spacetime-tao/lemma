from lemma.judge.prompt_sanitize import sanitize_miner_fenced_block


def test_sanitize_breaks_triple_backticks() -> None:
    raw = "hello ```json\n{}\n``` world"
    out = sanitize_miner_fenced_block("trace", raw)
    assert "```json" not in out or "``\u200b`json" in out
    assert out.startswith("```trace\n")


def test_sanitize_empty() -> None:
    assert "trace" in sanitize_miner_fenced_block("trace", None)
