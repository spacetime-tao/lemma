"""Judge JSON parsing."""

import pytest
from lemma.judge.json_util import parse_rubric_json


def test_parse_rubric_json_single_object_with_prefix_suffix() -> None:
    text = 'prefix {"coherence": 0.8, "exploration": 0.7, "clarity": 0.9} suffix'
    s = parse_rubric_json(text)
    assert s.composite == pytest.approx((0.8 + 0.7 + 0.9) / 3.0)


def test_parse_rubric_json_rejects_multiple_distinct_objects() -> None:
    text = (
        '{"coherence": 1.0, "exploration": 0.0, "clarity": 0.0} '
        '{"coherence": 0.0, "exploration": 1.0, "clarity": 0.0}'
    )
    with pytest.raises(ValueError, match="exactly one valid rubric"):
        parse_rubric_json(text)


def test_parse_rubric_json_rejects_extra_keys() -> None:
    text = '{"coherence": 0.5, "exploration": 0.5, "clarity": 0.5, "hack": 1}'
    with pytest.raises(ValueError, match=r"wrong_keys=1.*sample_wrong_keys="):
        parse_rubric_json(text)


def test_parse_rubric_json_rejects_out_of_range() -> None:
    text = '{"coherence": 1.5, "exploration": 0.5, "clarity": 0.5}'
    with pytest.raises(ValueError, match=r"out_of_range=1.*sample_out_of_range="):
        parse_rubric_json(text)


def test_parse_rubric_json_skips_junk_object_then_accepts_rubric() -> None:
    text = (
        '{"wrong": true} '
        '{"coherence": 0.8, "exploration": 0.7, "clarity": 0.9}'
    )
    s = parse_rubric_json(text)
    assert s.coherence == pytest.approx(0.8)
    assert s.exploration == pytest.approx(0.7)
    assert s.clarity == pytest.approx(0.9)


def test_parse_rubric_json_set_notation_preamble_then_rubric() -> None:
    text = (
        "Consider the set { x | x > 0 }. "
        '{"coherence": 0.6, "exploration": 0.5, "clarity": 0.4}'
    )
    s = parse_rubric_json(text)
    assert s.composite == pytest.approx((0.6 + 0.5 + 0.4) / 3.0)


def test_parse_rubric_json_exploration_first_after_prose() -> None:
    text = (
        "Here is my verdict. "
        '{"exploration": 0.2, "coherence": 0.3, "clarity": 0.4}'
    )
    s = parse_rubric_json(text)
    assert s.exploration == pytest.approx(0.2)
    assert s.coherence == pytest.approx(0.3)
    assert s.clarity == pytest.approx(0.4)


def test_parse_rubric_json_strips_markdown_fence() -> None:
    text = '```json\n{"coherence": 0.2, "exploration": 0.3, "clarity": 0.4}\n```'
    s = parse_rubric_json(text)
    assert s.composite == pytest.approx((0.2 + 0.3 + 0.4) / 3.0)
