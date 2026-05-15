"""Public cadence task export."""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from typing import Any, cast

from lemma import __version__
from lemma.common.config import LemmaSettings
from lemma.formal_campaigns import load_campaign_acceptances, load_campaigns, public_campaigns_payload
from lemma.ledger import LedgerSolver, SolvedLedgerEntry, matching_solved_ledger
from lemma.problems.base import Problem
from lemma.problems.factory import get_problem_source
from lemma.problems.generated import generated_registry_sha256
from lemma.problems.known_theorems import known_theorems_manifest_sha256


def build_miner_dashboard(settings: LemmaSettings, *, generated_unix: int | None = None) -> dict[str, Any]:
    """Build the public cadence task payload."""
    source = get_problem_source(settings)
    problems = source.all_problems()
    problems_by_id = {problem.id: problem for problem in problems}
    hashes = {problem.id: problem.theorem_statement_sha256() for problem in problems}
    ledger = matching_solved_ledger(settings.solved_ledger_path, hashes)
    solved_by_target = {entry.target_id: entry for entry in ledger}
    active = next((problem for problem in problems if problem.id not in solved_by_target), None)
    previous_target, current_target, next_target = _target_window(source, problems, solved_by_target)
    current = ledger[-1] if ledger else None
    manifest_sha256 = known_theorems_manifest_sha256(settings.known_theorems_manifest_path)
    receipts = _accepted_solver_receipts(ledger, problems_by_id)

    return {
        "schema_version": 4,
        "generated_unix": int(time.time() if generated_unix is None else generated_unix),
        "lemma_version": __version__,
        "problem_source": settings.problem_source,
        "known_theorems_manifest_sha256": manifest_sha256,
        "generated_registry_sha256": generated_registry_sha256(),
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
            "accepted_solver_receipts": len(receipts),
        },
        "active_target": _target_row(active, solved_by_target, active_id=active.id) if active is not None else None,
        "target_window": {
            "previous": _target_row(previous_target, solved_by_target, active_id=active.id if active else None)
            if previous_target is not None
            else None,
            "current": _target_row(current_target, solved_by_target, active_id=active.id if active else None)
            if current_target is not None
            else None,
            "next": _target_row(next_target, solved_by_target, active_id=active.id if active else None)
            if next_target is not None
            else None,
        },
        "targets": [
            _target_row(problem, solved_by_target, active_id=active.id if active else None) for problem in problems
        ],
        "current_solver_set": _solved_entry_row(current) if current is not None else None,
        "solved_ledger": [_solved_entry_row(entry) for entry in ledger],
        "accepted_solver_receipts": receipts,
    }


def write_miner_dashboard(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        "w",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
        encoding="utf-8",
    ) as f:
        tmp = Path(f.name)
        f.write(text)
    tmp.replace(path)


def build_bounty_dashboard(settings: LemmaSettings, *, generated_unix: int | None = None) -> dict[str, Any]:
    """Build the public Formal Conjectures bounty payload."""
    return public_campaigns_payload(
        load_campaigns(settings.formal_campaign_registry_path),
        acceptances=load_campaign_acceptances(settings.campaign_acceptance_ledger_path),
        generated_unix=generated_unix,
    )


def publish_public_dashboards(output_dir: Path, settings: LemmaSettings) -> tuple[Path, Path]:
    """Publish both public task feeds with atomic file replacement."""
    cadence_path = output_dir / "cadence.json"
    bounties_path = output_dir / "bounties.json"
    write_miner_dashboard(cadence_path, build_miner_dashboard(settings))
    write_miner_dashboard(bounties_path, build_bounty_dashboard(settings))
    return cadence_path, bounties_path


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
        "source_lane": str(problem.extra.get("source_lane") or problem.split),
        "source_url": str(problem.extra.get("source_url") or ""),
        "imports": list(problem.imports),
        "lean_toolchain": problem.lean_toolchain,
        "mathlib_rev": problem.mathlib_rev,
        "theorem_statement_sha256": problem.theorem_statement_sha256(),
    }
    if status == "active":
        row["challenge_source"] = problem.challenge_source()
        row["submission_stub"] = problem.submission_stub()
    if solved is not None:
        row["solved"] = {
            "accepted_block": solved.accepted_block,
            "accepted_unix": solved.accepted_unix,
            "solver_uids": list(solved.solver_uids),
            "solver_hotkeys": [solver.hotkey for solver in solved.solvers],
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
        "verify_reason": solver.verify_reason,
        "build_seconds": solver.build_seconds,
        "weight_share": 1.0 / solver_count,
    }


def _accepted_solver_receipts(
    ledger: list[SolvedLedgerEntry],
    problems_by_id: dict[str, Problem],
) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for entry in ledger:
        problem = problems_by_id.get(entry.target_id)
        if problem is None:
            continue
        for solver in entry.solvers:
            receipts.append(
                {
                    "target_id": entry.target_id,
                    "theorem_name": problem.theorem_name,
                    "theorem_statement_sha256": entry.theorem_statement_sha256,
                    "title": str(problem.extra.get("title") or entry.target_id),
                    "source_url": str(problem.extra.get("source_url") or ""),
                    "accepted_block": entry.accepted_block,
                    "accepted_unix": entry.accepted_unix,
                    "validator_hotkey": entry.validator_hotkey,
                    "lemma_version": entry.lemma_version,
                    "solver_uid": solver.uid,
                    "solver_hotkey": solver.hotkey,
                    "verify_reason": solver.verify_reason,
                    "build_seconds": solver.build_seconds,
                },
            )
    return receipts


def _target_window(
    source: Any,
    problems: list[Problem],
    solved_by_target: dict[str, SolvedLedgerEntry],
) -> tuple[Problem | None, Problem | None, Problem | None]:
    target_window = getattr(source, "target_window", None)
    if callable(target_window):
        return cast(tuple[Problem | None, Problem | None, Problem | None], target_window())
    active_index = next((idx for idx, problem in enumerate(problems) if problem.id not in solved_by_target), None)
    if active_index is None:
        previous = problems[-1] if problems else None
        return previous, None, None
    previous = problems[active_index - 1] if active_index > 0 else None
    current = problems[active_index]
    next_problem = problems[active_index + 1] if active_index + 1 < len(problems) else None
    return previous, current, next_problem
