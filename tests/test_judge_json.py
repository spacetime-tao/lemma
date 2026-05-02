"""Judge JSON parsing."""

import pytest
from lemma.judge.json_util import parse_rubric_json


def test_parse_rubric_json() -> None:
    text = 'prefix {"coherence": 0.8, "exploration": 0.7, "clarity": 0.9} suffix'
    s = parse_rubric_json(text)
    assert s.composite == pytest.approx((0.8 + 0.7 + 0.9) / 3.0)
