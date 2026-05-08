"""Training JSONL export payloads."""

from pathlib import Path

from lemma.judge.base import RubricScore
from lemma.protocol import LemmaChallenge, ReasoningStep
from lemma.validator.training_export import append_epoch_jsonl, training_record


def test_training_record_roundtrip_fields(tmp_path: Path) -> None:
    resp = LemmaChallenge(
        theorem_id="x",
        theorem_statement="theorem p : True := by sorry",
        imports=["Mathlib"],
        lean_toolchain="t",
        mathlib_rev="m",
        deadline_unix=0,
        metronome_id="z",
        reasoning_steps=[
            ReasoningStep(title="A", text="First."),
            ReasoningStep(text="Second."),
        ],
        proof_script="namespace Submission\n",
        model_card="prover=openai model=demo base_url=https://example.invalid/v1",
    )
    r = RubricScore(coherence=0.8, exploration=0.7, clarity=0.9, composite=0.8)
    row = training_record(block=42, theorem_id="tid", uid=7, resp=resp, rubric=r)
    assert row["schema_version"] == 1
    assert row["uid"] == 7
    assert row["theorem_id"] == "tid"
    assert row["reasoning_steps"] is not None
    assert len(row["reasoning_steps"]) == 2
    assert row["rubric"]["composite"] == 0.8
    assert "demo" in (row.get("model_card") or "")

    out = tmp_path / "train.jsonl"
    append_epoch_jsonl(out, [row], {7: 0.25})
    line = out.read_text(encoding="utf-8").strip()
    assert '"pareto_weight": 0.25' in line


def test_training_record_reasoning_only_no_scores(tmp_path: Path) -> None:
    resp = LemmaChallenge(
        theorem_id="x",
        theorem_statement="theorem p : True := by sorry",
        imports=["Mathlib"],
        lean_toolchain="t",
        mathlib_rev="m",
        deadline_unix=0,
        metronome_id="z",
        reasoning_steps=[ReasoningStep(title="A", text="First.")],
        proof_script="namespace Submission\n",
        model_card="m",
    )
    r = RubricScore(coherence=0.8, exploration=0.7, clarity=0.9, composite=0.8)
    row = training_record(
        block=1,
        theorem_id="tid",
        uid=3,
        resp=resp,
        rubric=r,
        profile="reasoning_only",
    )
    assert row["schema_version"] == 2
    assert row["export_profile"] == "reasoning_only"
    assert "proof_script" not in row
    assert "rubric" not in row

    out = tmp_path / "r.jsonl"
    append_epoch_jsonl(out, [row], {3: 0.5}, include_pareto_weights=False)
    line = out.read_text(encoding="utf-8").strip()
    assert "pareto_weight" not in line
