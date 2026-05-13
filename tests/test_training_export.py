"""Training JSONL export payloads."""

from pathlib import Path

from lemma.judge.base import RubricScore
from lemma.lean.proof_metrics import LeanProofMetrics
from lemma.protocol import LemmaChallenge
from lemma.validator.training_export import append_epoch_jsonl, round_summary_record, training_record


def test_training_record_roundtrip_fields(tmp_path: Path) -> None:
    resp = LemmaChallenge(
        theorem_id="x",
        theorem_statement="theorem p : True := by sorry",
        imports=["Mathlib"],
        lean_toolchain="t",
        mathlib_rev="m",
        deadline_unix=0,
        metronome_id="z",
        proof_script="namespace Submission\n",
        model_card="prover=openai model=demo base_url=https://example.invalid/v1",
    )
    r = RubricScore(coherence=0.8, exploration=0.7, clarity=0.9, composite=0.8)
    proof_metrics = LeanProofMetrics(
        proof_declaration_bytes=538,
        proof_declaration_lines=9,
        probe_exit_code=0,
        proof_declaration_delimiters=21,
        proof_declaration_max_depth=5,
    )
    export_context = {
        "lemma_version": "0.1.0",
        "judge_profile_sha256": "a" * 64,
        "judge_rubric_sha256": "b" * 64,
        "generated_registry_sha256": "c" * 64,
    }
    row = training_record(
        block=42,
        theorem_id="tid",
        uid=7,
        resp=resp,
        rubric=r,
        proof_metrics=proof_metrics,
        coldkey="coldkey-public",
        export_context=export_context,
    )
    assert row["schema_version"] == 1
    assert row["export_profile"] == "full"
    assert row["uid"] == 7
    assert row["coldkey"] == "coldkey-public"
    assert row["export_context"] == export_context
    assert row["theorem_id"] == "tid"
    assert row["theorem_statement"] == "theorem p : True := by sorry"
    assert row["rubric"]["composite"] == 0.8
    assert row["proof_metrics"]["proof_declaration_bytes"] == 538
    assert row["proof_metrics"]["proof_declaration_lines"] == 9
    assert row["proof_metrics"]["probe_exit_code"] == 0
    assert row["proof_metrics"]["proof_declaration_delimiters"] == 21
    assert row["proof_metrics"]["proof_declaration_max_depth"] == 5
    assert "demo" in (row.get("model_card") or "")

    out = tmp_path / "train.jsonl"
    append_epoch_jsonl(out, [row], {7: 0.25})
    line = out.read_text(encoding="utf-8").strip()
    assert '"pareto_weight": 0.25' in line
    assert '"proof_metrics":' in line


def test_training_record_summary_no_scores(tmp_path: Path) -> None:
    resp = LemmaChallenge(
        theorem_id="x",
        theorem_statement="theorem p : True := by sorry",
        imports=["Mathlib"],
        lean_toolchain="t",
        mathlib_rev="m",
        deadline_unix=0,
        metronome_id="z",
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
        profile="summary",
        export_context={"lemma_version": "0.1.0"},
    )
    assert row["schema_version"] == 2
    assert row["export_profile"] == "summary"
    assert row["export_context"] == {"lemma_version": "0.1.0"}
    assert "proof_script" not in row
    assert "theorem_statement" not in row
    assert "rubric" not in row
    assert "proof_metrics" not in row
    assert "coldkey" not in row

    out = tmp_path / "r.jsonl"
    append_epoch_jsonl(out, [row], {3: 0.5}, include_pareto_weights=False)
    line = out.read_text(encoding="utf-8").strip()
    assert "pareto_weight" not in line
    assert "proof_metrics" not in line


def test_round_summary_record_exports_zero_pass_round(tmp_path: Path) -> None:
    row = round_summary_record(
        block=10,
        theorem_id="gen/10",
        passed_uids=set(),
        export_context={"lemma_version": "0.1.0"},
    )

    assert row == {
        "schema_version": 2,
        "record_type": "round_summary",
        "block": 10,
        "theorem_id": "gen/10",
        "passed_uids": [],
        "export_context": {"lemma_version": "0.1.0"},
    }

    out = tmp_path / "summary.jsonl"
    append_epoch_jsonl(out, [row], {3: 0.5})
    line = out.read_text(encoding="utf-8").strip()
    assert "pareto_weight" not in line


def test_training_record_rejects_legacy_reasoning_only_alias() -> None:
    resp = LemmaChallenge(
        theorem_id="x",
        theorem_statement="theorem p : True := by sorry",
        imports=["Mathlib"],
        lean_toolchain="t",
        mathlib_rev="m",
        deadline_unix=0,
        metronome_id="z",
        proof_script="namespace Submission\n",
    )

    try:
        training_record(block=1, theorem_id="tid", uid=3, resp=resp, profile="reasoning_only")  # type: ignore[arg-type]
    except ValueError as e:
        assert "unsupported training export profile" in str(e)
    else:
        raise AssertionError("legacy reasoning_only profile should fail")
