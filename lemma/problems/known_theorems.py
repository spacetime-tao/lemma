"""Pinned known-theorem problem source for Lemma."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

from lemma.ledger import solved_target_ids
from lemma.problems.base import Problem, ProblemSource

KNOWN_THEOREMS_MANIFEST_PATH = Path(__file__).resolve().parent / "known_theorems_manifest.json"
_REQUIRED_TARGET_KEYS = frozenset(
    {
        "id",
        "order",
        "title",
        "difficulty",
        "imports",
        "theorem_name",
        "type_expr",
        "challenge_full",
        "submission_stub",
        "human_proof_reference",
        "attribution",
        "review",
    }
)


def _manifest_path(path: Path | None = None) -> Path:
    return path or KNOWN_THEOREMS_MANIFEST_PATH


def known_theorems_manifest(path: Path | None = None) -> dict[str, Any]:
    raw = _manifest_path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    validate_known_theorems_manifest(data)
    return cast(dict[str, Any], data)


def validate_known_theorems_manifest(data: dict[str, Any]) -> None:
    errors: list[str] = []
    if int(data.get("schema_version", 0)) != 1:
        errors.append("schema_version must be 1")
    source = data.get("source")
    if not isinstance(source, dict):
        errors.append("source object is required")
        source = {}
    for key in ("commit", "lean_toolchain", "mathlib_rev", "license_note"):
        if not str(source.get(key) or "").strip():
            errors.append(f"source.{key} is required")
    targets = data.get("targets")
    if not isinstance(targets, list) or not targets:
        errors.append("targets must be a non-empty array")
        targets = []

    seen_ids: set[str] = set()
    seen_orders: set[int] = set()
    for idx, target in enumerate(targets):
        if not isinstance(target, dict):
            errors.append(f"target {idx}: expected object")
            continue
        missing = sorted(k for k in _REQUIRED_TARGET_KEYS if not target.get(k))
        if missing:
            errors.append(f"target {idx}: missing {', '.join(missing)}")
        tid = str(target.get("id") or "")
        if not tid.startswith("known/"):
            errors.append(f"target {idx}: id must start with 'known/'")
        if tid in seen_ids:
            errors.append(f"target {idx}: duplicate id {tid!r}")
        seen_ids.add(tid)
        try:
            order = int(str(target.get("order")))
        except (TypeError, ValueError):
            errors.append(f"target {idx}: order must be an integer")
            continue
        if order in seen_orders:
            errors.append(f"target {idx}: duplicate order {order}")
        seen_orders.add(order)

        proof_ref = target.get("human_proof_reference")
        if not isinstance(proof_ref, dict) or not str(proof_ref.get("citation") or "").strip():
            errors.append(f"target {idx} id={tid!r}: human_proof_reference.citation is required")
        imports = target.get("imports")
        if (
            not isinstance(imports, list)
            or not imports
            or any(not isinstance(item, str) or not item.strip() for item in imports)
        ):
            errors.append(f"target {idx} id={tid!r}: imports must be a non-empty string array")
        review = target.get("review")
        if not isinstance(review, dict):
            errors.append(f"target {idx} id={tid!r}: review object is required")
            review = {}
        if review.get("known_math") is not True:
            errors.append(f"target {idx} id={tid!r}: review.known_math must be true")
        if review.get("already_formalized_in_lean") is True:
            errors.append(f"target {idx} id={tid!r}: already formalized targets are not eligible")
        if review.get("accepted_lean_proof_known") is True:
            errors.append(f"target {idx} id={tid!r}: targets with known accepted Lean proofs are not eligible")
        for key in ("reviewer", "reviewed_at", "duplicate_check", "statement_faithfulness"):
            if not str(review.get(key) or "").strip():
                errors.append(f"target {idx} id={tid!r}: review.{key} is required")
        if "sorry" not in str(target.get("challenge_full") or ""):
            errors.append(f"target {idx} id={tid!r}: challenge_full should contain the unproved theorem stub")
    if errors:
        raise ValueError("known theorem manifest failed validation:\n- " + "\n- ".join(errors))


def known_theorems_manifest_sha256(path: Path | None = None) -> str:
    data = known_theorems_manifest(path)
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class KnownTheoremsSource(ProblemSource):
    """Ordered source: first unsolved known-theorem target is active."""

    def __init__(self, manifest_path: Path | None = None, ledger_path: Path | None = None) -> None:
        self._manifest_path = _manifest_path(manifest_path)
        self._ledger_path = ledger_path
        self._manifest = known_theorems_manifest(self._manifest_path)
        rows = sorted(self._manifest["targets"], key=lambda row: int(row["order"]))
        self._problems = [_row_to_problem(row, source=self._manifest["source"]) for row in rows]

    def all_problems(self) -> list[Problem]:
        return list(self._problems)

    def sample(self, seed: int, split: str | None = None) -> Problem:
        hashes = {problem.id: problem.theorem_statement_sha256() for problem in self._problems}
        solved = solved_target_ids(self._ledger_path, hashes)
        for problem in self._problems:
            if problem.id not in solved:
                return problem
        raise ValueError("all known-theorem targets in the manifest are solved")

    def get(self, problem_id: str) -> Problem:
        for problem in self._problems:
            if problem.id == problem_id:
                return problem
        raise KeyError(problem_id)


def _row_to_problem(row: dict[str, Any], *, source: dict[str, Any]) -> Problem:
    imports = tuple(str(item).strip() for item in row["imports"])
    extra = {
        "source_lane": "known_theorems",
        "title": str(row["title"]),
        "order": int(row["order"]),
        "difficulty": str(row.get("difficulty") or "unlabeled"),
        "upstream_repo": str(source.get("repo") or ""),
        "upstream_commit": str(source.get("commit") or ""),
        "license_note": str(source.get("license_note") or ""),
        "human_proof_reference": row["human_proof_reference"],
        "attribution": row["attribution"],
        "review": row["review"],
        "challenge_full": str(row["challenge_full"]),
        "submission_stub": str(row["submission_stub"]),
    }
    return Problem(
        id=str(row["id"]),
        theorem_name=str(row["theorem_name"]),
        type_expr=str(row["type_expr"]),
        split="known_theorems",
        lean_toolchain=str(source["lean_toolchain"]),
        mathlib_rev=str(source["mathlib_rev"]),
        imports=imports,
        extra=extra,
    )
