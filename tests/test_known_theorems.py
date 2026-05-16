from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from lemma.problems.known_theorems import (
    KnownTheoremsSource,
    known_theorems_manifest_sha256,
    validate_known_theorems_manifest,
)


def _target(target_id: str, order: int, theorem_name: str = "target") -> dict[str, object]:
    return {
        "id": target_id,
        "order": order,
        "title": target_id,
        "difficulty": "starter",
        "imports": ["Mathlib"],
        "theorem_name": theorem_name,
        "type_expr": "True",
        "challenge_full": (
            "import Mathlib\n\n"
            "namespace Submission\n\n"
            f"theorem {theorem_name} : True := by\n"
            "  sorry\n\n"
            "end Submission\n"
        ),
        "submission_stub": (
            "import Mathlib\n\n"
            "namespace Submission\n\n"
            f"theorem {theorem_name} : True := by\n"
            "  sorry\n\n"
            "end Submission\n"
        ),
        "human_proof_reference": {
            "citation": "Trivial known theorem.",
            "url": "https://example.test/proof",
            "proof_status": "known",
        },
        "attribution": {"source": "test", "license_note": "test-only"},
        "review": {
            "known_math": True,
            "already_formalized_in_lean": False,
            "accepted_lean_proof_known": False,
            "reviewer": "test",
            "reviewed_at": "2026-05-14",
            "duplicate_check": "test duplicate search",
            "statement_faithfulness": "test statement review",
        },
    }


def _manifest(targets: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "source": {
            "repo": "curated-local",
            "commit": "abc123",
            "lean_toolchain": "leanprover/lean4:v4.27.0",
            "mathlib_rev": "def456",
            "license_note": "test-only",
        },
        "targets": targets,
    }


def _write_manifest(path: Path, targets: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(_manifest(targets), sort_keys=True), encoding="utf-8")


def _statement_hash(theorem_name: str) -> str:
    source = (
        "import Mathlib\n\n"
        "namespace Submission\n\n"
        f"theorem {theorem_name} : True := by\n"
        "  sorry\n\n"
        "end Submission\n"
    )
    return hashlib.sha256((source.strip() + "\n").encode("utf-8")).hexdigest()


def test_known_theorem_manifest_is_deterministically_ordered(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(
        manifest_path,
        [
            _target("known/test/second", 2, "second"),
            _target("known/test/first", 1, "first"),
        ],
    )

    src = KnownTheoremsSource(manifest_path=manifest_path, ledger_path=tmp_path / "ledger.jsonl")

    assert [p.id for p in src.all_problems()] == ["known/test/first", "known/test/second"]
    assert src.sample(seed=999).id == "known/test/second"
    assert src.all_problems()[0].imports == ("Mathlib",)
    assert len(known_theorems_manifest_sha256(manifest_path)) == 64


def test_known_theorem_manifest_rejects_already_formalized_target() -> None:
    row = _target("known/test/formalized", 1)
    review = row["review"]
    assert isinstance(review, dict)
    review["already_formalized_in_lean"] = True

    with pytest.raises(ValueError, match="already formalized"):
        validate_known_theorems_manifest(_manifest([row]))


def test_known_theorem_manifest_requires_human_proof_citation() -> None:
    row = _target("known/test/no-citation", 1)
    proof_ref = row["human_proof_reference"]
    assert isinstance(proof_ref, dict)
    proof_ref["citation"] = ""

    with pytest.raises(ValueError, match="human_proof_reference.citation"):
        validate_known_theorems_manifest(_manifest([row]))


def test_known_theorem_source_ignores_ledger_for_fixed_cadence(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    ledger_path = tmp_path / "ledger.jsonl"
    _write_manifest(
        manifest_path,
        [
            _target("known/test/first", 1, "first"),
            _target("known/test/second", 2, "second"),
        ],
    )
    ledger_path.write_text(
        json.dumps(
            {
                "target_id": "known/test/first",
                "winner_uid": 7,
                "winner_hotkey": "hot",
                "winner_coldkey": "cold",
                "proof_sha256": "a" * 64,
                "accepted_block": 10,
                "accepted_unix": 20,
                "validator_hotkey": "validator",
                "lemma_version": "0.1.0",
                "verify_reason": "ok",
                "build_seconds": 1.0,
                "theorem_statement_sha256": _statement_hash("first"),
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    src = KnownTheoremsSource(manifest_path=manifest_path, ledger_path=ledger_path)

    assert src.sample(seed=0).id == "known/test/first"


def test_known_theorem_source_ignores_stale_ledger_hash(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    ledger_path = tmp_path / "ledger.jsonl"
    _write_manifest(
        manifest_path,
        [
            _target("known/test/first", 1, "first"),
            _target("known/test/second", 2, "second"),
        ],
    )
    ledger_path.write_text(
        json.dumps(
            {
                "target_id": "known/test/first",
                "winner_uid": 7,
                "winner_hotkey": "hot",
                "winner_coldkey": "cold",
                "proof_sha256": "a" * 64,
                "accepted_block": 10,
                "accepted_unix": 20,
                "validator_hotkey": "validator",
                "lemma_version": "0.1.0",
                "verify_reason": "ok",
                "build_seconds": 1.0,
                "theorem_statement_sha256": "stale",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    src = KnownTheoremsSource(manifest_path=manifest_path, ledger_path=ledger_path)

    assert src.sample(seed=0).id == "known/test/first"


def test_known_theorem_manifest_fingerprint_changes_on_target_contract_changes(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    row = _target("known/test/one", 1, "one")
    _write_manifest(manifest_path, [row])
    baseline = known_theorems_manifest_sha256(manifest_path)

    changed_order = deepcopy(row)
    changed_order["order"] = 2
    _write_manifest(manifest_path, [changed_order])
    assert known_theorems_manifest_sha256(manifest_path) != baseline

    changed_citation = deepcopy(row)
    proof_ref = changed_citation["human_proof_reference"]
    assert isinstance(proof_ref, dict)
    proof_ref["citation"] = "A different proof citation."
    _write_manifest(manifest_path, [changed_citation])
    assert known_theorems_manifest_sha256(manifest_path) != baseline

    changed_statement = deepcopy(row)
    changed_statement["type_expr"] = "True = True"
    changed_statement["challenge_full"] = (
        "import Mathlib\n\n"
        "namespace Submission\n\n"
        "theorem one : True = True := by\n"
        "  sorry\n\n"
        "end Submission\n"
    )
    _write_manifest(manifest_path, [changed_statement])
    assert known_theorems_manifest_sha256(manifest_path) != baseline
