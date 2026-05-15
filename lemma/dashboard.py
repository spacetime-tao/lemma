"""Public miner dashboard export."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from lemma import __version__
from lemma.common.config import LemmaSettings
from lemma.ledger import LedgerSolver, SolvedLedgerEntry, matching_solved_ledger
from lemma.problems.base import Problem
from lemma.problems.known_theorems import KnownTheoremsSource, known_theorems_manifest_sha256


def build_miner_dashboard(settings: LemmaSettings, *, generated_unix: int | None = None) -> dict[str, Any]:
    """Build the public, static miner target board payload."""
    source = KnownTheoremsSource(settings.known_theorems_manifest_path, settings.solved_ledger_path)
    problems = source.all_problems()
    problems_by_id = {problem.id: problem for problem in problems}
    hashes = {problem.id: problem.theorem_statement_sha256() for problem in problems}
    ledger = matching_solved_ledger(settings.solved_ledger_path, hashes)
    solved_by_target = {entry.target_id: entry for entry in ledger}
    active = next((problem for problem in problems if problem.id not in solved_by_target), None)
    current = ledger[-1] if ledger else None
    manifest_sha256 = known_theorems_manifest_sha256(settings.known_theorems_manifest_path)
    receipts = _accepted_proof_receipts(ledger, problems_by_id, manifest_sha256)

    return {
        "schema_version": 3,
        "generated_unix": int(time.time() if generated_unix is None else generated_unix),
        "lemma_version": __version__,
        "problem_source": "known_theorems",
        "manifest_sha256": manifest_sha256,
        "reward": {
            "mode": "current_epoch_observed_difficulty_with_owner_burn",
            "rule": "Verified current-epoch proofs earn (1 - solve_fraction)^2 of the budget.",
            "rank_policy": "commitment_block_ranked; same_rank_commitments_tie",
            "owner_burn_uid": int(settings.owner_burn_uid),
        },
        "counts": {
            "total_targets": len(problems),
            "solved_targets": sum(1 for problem in problems if problem.id in solved_by_target),
            "remaining_targets": sum(1 for problem in problems if problem.id not in solved_by_target),
            "current_solver_count": 0 if current is None else len(current.solvers),
            "accepted_proof_receipts": len(receipts),
        },
        "active_target": _target_row(active, solved_by_target, active_id=active.id) if active is not None else None,
        "targets": [
            _target_row(problem, solved_by_target, active_id=active.id if active else None) for problem in problems
        ],
        "current_solver_set": _solved_entry_row(current) if current is not None else None,
        "solved_ledger": [_solved_entry_row(entry) for entry in ledger],
        "accepted_proof_receipts": receipts,
    }


def write_miner_dashboard(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _target_row(
    problem: Problem,
    solved_by_target: dict[str, SolvedLedgerEntry],
    *,
    active_id: str | None = None,
) -> dict[str, Any]:
    solved = solved_by_target.get(problem.id)
    status = "solved" if solved is not None else "active" if problem.id == active_id else "queued"
    row = {
        "id": problem.id,
        "order": int(problem.extra.get("order") or 0),
        "title": str(problem.extra.get("title") or problem.id),
        "difficulty": str(problem.extra.get("difficulty") or "unlabeled"),
        "status": status,
        "theorem_name": problem.theorem_name,
        "imports": list(problem.imports),
        "lean_toolchain": problem.lean_toolchain,
        "mathlib_rev": problem.mathlib_rev,
        "theorem_statement_sha256": problem.theorem_statement_sha256(),
    }
    if status == "active":
        row["challenge_source"] = problem.challenge_source()
    if solved is not None:
        row["solved"] = {
            "accepted_block": solved.accepted_block,
            "accepted_unix": solved.accepted_unix,
            "solver_uids": list(solved.solver_uids),
            "proof_sha256": [solver.proof_sha256 for solver in solved.solvers],
            "commitment_hash": [solver.commitment_hash for solver in solved.solvers],
            "commitment_block": [solver.commitment_block for solver in solved.solvers],
            "commit_cutoff_block": [solver.commit_cutoff_block for solver in solved.solvers],
        }
    return row


def _solved_entry_row(entry: SolvedLedgerEntry) -> dict[str, Any]:
    return {
        "target_id": entry.target_id,
        "accepted_block": entry.accepted_block,
        "accepted_unix": entry.accepted_unix,
        "validator_hotkey": entry.validator_hotkey,
        "lemma_version": entry.lemma_version,
        "theorem_statement_sha256": entry.theorem_statement_sha256,
        "solvers": [_solver_row(solver, len(entry.solvers)) for solver in entry.solvers],
    }


def _solver_row(solver: LedgerSolver, solver_count: int) -> dict[str, Any]:
    return {
        "uid": solver.uid,
        "hotkey": solver.hotkey,
        "proof_sha256": solver.proof_sha256,
        "commitment_hash": solver.commitment_hash,
        "commitment_block": solver.commitment_block,
        "commit_cutoff_block": solver.commit_cutoff_block,
        "verify_reason": solver.verify_reason,
        "build_seconds": solver.build_seconds,
        "weight_share": 1.0 / solver_count,
    }


def _accepted_proof_receipts(
    ledger: list[SolvedLedgerEntry],
    problems_by_id: dict[str, Problem],
    manifest_sha256: str,
) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for entry in ledger:
        problem = problems_by_id.get(entry.target_id)
        if problem is None:
            continue
        for solver in entry.solvers:
            if not solver.proof_script:
                continue
            receipt = {
                "target_id": entry.target_id,
                "theorem_name": problem.theorem_name,
                "manifest_sha256": manifest_sha256,
                "theorem_statement_sha256": entry.theorem_statement_sha256,
                "challenge_source": problem.challenge_source(),
                "imports": list(problem.imports),
                "lean_toolchain": problem.lean_toolchain,
                "mathlib_rev": problem.mathlib_rev,
                "accepted_block": entry.accepted_block,
                "accepted_unix": entry.accepted_unix,
                "validator_hotkey": entry.validator_hotkey,
                "lemma_version": entry.lemma_version,
                "solver_uid": solver.uid,
                "solver_hotkey": solver.hotkey,
                "proof_sha256": solver.proof_sha256,
                "proof_nonce": solver.proof_nonce,
                "commitment_hash": solver.commitment_hash,
                "commitment_first_seen_block": solver.commitment_block,
                "commit_cutoff_block": solver.commit_cutoff_block,
                "proof_script": solver.proof_script,
                "verify_reason": solver.verify_reason,
                "build_seconds": solver.build_seconds,
            }
            receipt["receipt_sha256"] = _receipt_sha256(receipt)
            receipts.append(receipt)
    return receipts


def _receipt_sha256(receipt: dict[str, Any]) -> str:
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
