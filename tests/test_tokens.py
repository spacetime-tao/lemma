from lemma.scoring.tokens import count_tokens


def test_count_tokens_is_trace_length_proxy() -> None:
    assert count_tokens("") == 0
    assert count_tokens("abc") == 3
    assert count_tokens("a\nb") == 3
