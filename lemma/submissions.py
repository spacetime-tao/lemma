"""Local pending proof store for manual proof miners."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from lemma.problems.base import Problem


def default_submissions_path() -> Path:
    return Path.home() / ".lemma" / "submissions.json"


def resolved_submissions_path(path: Path | None) -> Path:
    return path or default_submissions_path()


def theorem_statement_sha256(problem: Problem) -> str:
    return hashlib.sha256(problem.challenge_source().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PendingSubmission:
    target_id: str
    theorem_statement_sha256: str
    proof_sha256: str
    proof_script: str
    submitted_unix: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PendingSubmission:
        return cls(
            target_id=str(data["target_id"]),
            theorem_statement_sha256=str(data["theorem_statement_sha256"]),
            proof_sha256=str(data["proof_sha256"]),
            proof_script=str(data["proof_script"]),
            submitted_unix=int(data["submitted_unix"]),
        )


def load_pending_submissions(path: Path | None = None) -> dict[str, PendingSubmission]:
    store_path = resolved_submissions_path(path)
    if not store_path.exists():
        return {}
    raw = json.loads(store_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"submission store must be a JSON object: {store_path}")
    out: dict[str, PendingSubmission] = {}
    for target_id, row in raw.items():
        if not isinstance(row, dict):
            raise ValueError(f"invalid submission row for {target_id!r}")
        sub = PendingSubmission.from_dict(row)
        out[str(target_id)] = sub
    return out


def save_pending_submission(path: Path | None, problem: Problem, proof_script: str) -> PendingSubmission:
    proof = proof_script.strip() + "\n"
    if not proof.strip():
        raise ValueError("proof_script is empty")
    entry = PendingSubmission(
        target_id=problem.id,
        theorem_statement_sha256=theorem_statement_sha256(problem),
        proof_sha256=hashlib.sha256(proof.encode("utf-8")).hexdigest(),
        proof_script=proof,
        submitted_unix=int(time.time()),
    )
    rows = load_pending_submissions(path)
    rows[problem.id] = entry
    store_path = resolved_submissions_path(path)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {target_id: asdict(row) for target_id, row in sorted(rows.items())}
    store_path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return entry


def pending_submission_for_problem(path: Path | None, problem: Problem) -> PendingSubmission | None:
    entry = load_pending_submissions(path).get(problem.id)
    if entry is None:
        return None
    if entry.theorem_statement_sha256 != theorem_statement_sha256(problem):
        return None
    return entry
