"""Public cadence task export."""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from typing import Any

from lemma import __version__
from lemma.cadence import (
    DIFFICULTY_SCORE_WEIGHTS,
    SPLIT_WEIGHTS,
    cadence_problem,
    cadence_window,
    format_eta,
    next_seed,
    previous_seed,
)
from lemma.common.config import LemmaSettings
from lemma.common.subtensor import get_subtensor
from lemma.formal_campaigns import load_campaign_acceptances, load_campaigns, public_campaigns_payload
from lemma.ledger import LedgerSolver, SolvedLedgerEntry, load_solved_ledger
from lemma.problems.base import Problem
from lemma.problems.factory import get_problem_source
from lemma.problems.generated import GENERATED_SUPPLY_COUNT, generated_registry_sha256
from lemma.problems.known_theorems import known_theorems_manifest_sha256


def build_miner_dashboard(
    settings: LemmaSettings,
    *,
    generated_unix: int | None = None,
    current_block: int | None = None,
) -> dict[str, Any]:
    """Build the public cadence task payload."""
    source = get_problem_source(settings)
    block = _current_block(settings, current_block)
    window = cadence_window(block, settings.cadence_window_blocks)
    previous_target = cadence_problem(source, previous_seed(window.seed, window.window_blocks))
    current_target = cadence_problem(source, window.seed)
    next_target = cadence_problem(source, next_seed(window.seed, window.window_blocks))
    ledger = _load_public_ledger(settings, source)
    current_entries = [
        entry for entry in ledger if window.start_block <= int(entry.accepted_block) <= window.end_block
    ]
    current = _solver_set_for_entries(current_entries, current_target)
    manifest_sha256 = known_theorems_manifest_sha256(settings.known_theorems_manifest_path)
    receipts = _accepted_solver_receipts(ledger, source)
    targets = [
        _target_row(
            previous_target,
            status="previous",
            window_seed=previous_seed(window.seed, window.window_blocks),
            ledger=ledger,
        ),
        _target_row(current_target, status="current", window_seed=window.seed, ledger=ledger),
        _target_row(
            next_target,
            status="next",
            window_seed=next_seed(window.seed, window.window_blocks),
            ledger=ledger,
        ),
    ]

    return {
        "schema_version": 5,
        "generated_unix": int(time.time() if generated_unix is None else generated_unix),
        "lemma_version": __version__,
        "block": block,
        "seed": window.seed,
        "problem_source": settings.problem_source,
        "known_theorems_manifest_sha256": manifest_sha256,
        "generated_registry_sha256": generated_registry_sha256(),
        "cadence": {
            "block": block,
            "seed": window.seed,
            "window_blocks": window.window_blocks,
            "window_start_block": window.start_block,
            "window_end_block": window.end_block,
            "next_rotation_block": window.next_rotation_block,
            "blocks_until_rotation": window.blocks_until_rotation,
            "next_rotation_eta_seconds": window.eta_seconds(settings.block_time_sec_estimate),
            "next_rotation_eta": format_eta(window.eta_seconds(settings.block_time_sec_estimate)),
            "variants_enabled": bool(settings.lemma_uid_variant_problems),
            "split_weights": dict(SPLIT_WEIGHTS),
            "difficulty_scoring_weights": {
                **DIFFICULTY_SCORE_WEIGHTS,
                "easy": float(settings.lemma_scoring_difficulty_easy),
                "medium": float(settings.lemma_scoring_difficulty_medium),
                "hard": float(settings.lemma_scoring_difficulty_hard),
                "extreme": float(settings.lemma_scoring_difficulty_extreme),
            },
        },
        "reward": {
            "mode": "difficulty_weighted_rolling_score",
            "rule": "Verified proofs update per-UID rolling scores; positive rolling scores normalize into weights.",
            "coldkey_partitioning": bool(settings.lemma_scoring_coldkey_partition),
            "coldkey_partitioning_note": (
                "Same-coldkey partitioning applies work/reward pressure; it is not Sybil-proof identity."
            ),
        },
        "counts": {
            "total_targets": len(source.all_problems()) or GENERATED_SUPPLY_COUNT,
            "accepted_windows": len(
                {entry.accepted_block // max(1, int(settings.cadence_window_blocks)) for entry in ledger},
            ),
            "accepted_targets": len({entry.target_id for entry in ledger}),
            "current_solver_count": 0 if current is None else len(current.solvers),
            "accepted_solver_receipts": len(receipts),
        },
        "active_target": _target_row(current_target, status="current", window_seed=window.seed, ledger=ledger),
        "target_window": {
            "previous": targets[0],
            "current": targets[1],
            "next": targets[2],
        },
        "targets": targets,
        "current_solver_set": _solved_entry_row(current) if current is not None else None,
        "solved_ledger": [_solved_entry_row(entry) for entry in ledger],
        "accepted_solver_receipts": receipts,
        "accepted_proof_receipts": receipts,
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


def _current_block(settings: LemmaSettings, current_block: int | None) -> int:
    if current_block is not None:
        return int(current_block)
    try:
        return int(get_subtensor(settings).get_current_block())
    except Exception:
        return int(settings.target_genesis_block or 0)


def _load_public_ledger(settings: LemmaSettings, source: Any) -> list[SolvedLedgerEntry]:
    entries: list[SolvedLedgerEntry] = []
    for entry in load_solved_ledger(settings.solved_ledger_path):
        try:
            problem = source.get(entry.target_id)
        except KeyError:
            continue
        if problem.theorem_statement_sha256() == entry.theorem_statement_sha256:
            entries.append(entry)
    return entries


def _solver_set_for_entries(entries: list[SolvedLedgerEntry], fallback_problem: Problem) -> SolvedLedgerEntry | None:
    solvers: list[LedgerSolver] = []
    for entry in entries:
        solvers.extend(entry.solvers)
    if not solvers:
        return None
    latest = max(entries, key=lambda entry: entry.accepted_block)
    return SolvedLedgerEntry(
        target_id=fallback_problem.id,
        solvers=tuple(solvers),
        accepted_block=latest.accepted_block,
        accepted_unix=latest.accepted_unix,
        validator_hotkey=latest.validator_hotkey,
        lemma_version=latest.lemma_version,
        theorem_statement_sha256=fallback_problem.theorem_statement_sha256(),
    )


def _target_row(
    problem: Problem,
    *,
    status: str,
    window_seed: int,
    ledger: list[SolvedLedgerEntry],
) -> dict[str, Any]:
    solved = [entry for entry in ledger if entry.target_id == problem.id]
    row = {
        "id": problem.id,
        "order": int(problem.extra.get("order") or 0),
        "title": str(problem.extra.get("title") or problem.id),
        "difficulty": str(problem.extra.get("difficulty") or "unlabeled"),
        "status": status,
        "theorem_name": problem.theorem_name,
        "split": problem.split,
        "topic": str(problem.extra.get("topic") or problem.extra.get("source_lane") or problem.split),
        "window_seed": int(window_seed),
        "source_lane": str(problem.extra.get("source_lane") or problem.split),
        "source_url": str(problem.extra.get("source_url") or ""),
        "imports": list(problem.imports),
        "lean_toolchain": problem.lean_toolchain,
        "mathlib_rev": problem.mathlib_rev,
        "theorem_statement_sha256": problem.theorem_statement_sha256(),
    }
    if status == "current":
        row["challenge_source"] = problem.challenge_source()
        row["submission_stub"] = problem.submission_stub()
    if solved:
        latest = solved[-1]
        row["solved"] = {
            "accepted_block": latest.accepted_block,
            "accepted_unix": latest.accepted_unix,
            "solver_uids": list(latest.solver_uids),
            "solver_hotkeys": [solver.hotkey for solver in latest.solvers],
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
    source: Any,
) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for entry in ledger:
        try:
            problem = source.get(entry.target_id)
        except KeyError:
            continue
        for solver in entry.solvers:
            receipts.append(
                {
                    "target_id": entry.target_id,
                    "theorem_name": problem.theorem_name,
                    "theorem_statement_sha256": entry.theorem_statement_sha256,
                    "title": str(problem.extra.get("title") or entry.target_id),
                    "difficulty": str(problem.extra.get("difficulty") or problem.split),
                    "split": problem.split,
                    "topic": str(problem.extra.get("topic") or problem.extra.get("source_lane") or problem.split),
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
