"""Replay exported rewards under dedup and simple sybil-copy probes."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from lemma.scoring.dedup import dedup_coldkeys, dedup_identical_submissions, submission_fingerprint
from lemma.scoring.pareto import ScoredEntry, pareto_weights

DEFAULT_PROOF_WEIGHT = 0.0
MIN_DECISION_REPLAYABLE_ROWS = 50
MIN_DECISION_EPOCHS = 5
MIN_DECISION_UIDS = 5
MIN_DECISION_THEOREMS = 5


@dataclass(frozen=True)
class ReplayRow:
    block: int
    theorem_id: str
    uid: int
    coldkey: str | None
    entry: ScoredEntry


@dataclass(frozen=True)
class ReplayReport:
    total_rows: int
    invalid_json_lines: int
    replay_rows: list[ReplayRow]


@dataclass(frozen=True)
class ReplayOutcome:
    name: str
    entries_weighted: int
    identical_dropped: int
    coldkey_dropped: int
    weights: dict[int, float]

    @property
    def top_uid(self) -> int | None:
        if not self.weights:
            return None
        return max(self.weights, key=lambda uid: self.weights[uid])

    @property
    def top_weight(self) -> float:
        uid = self.top_uid
        return self.weights.get(uid, 0.0) if uid is not None else 0.0


@dataclass(frozen=True)
class ClonePressure:
    source_uid: int
    base_share: float
    group_share: float
    extra_share: float
    outcome: ReplayOutcome


def load_report(path: Path, *, proof_weight: float = DEFAULT_PROOF_WEIGHT) -> ReplayReport:
    _ = proof_weight
    total = 0
    invalid = 0
    rows: list[ReplayRow] = []
    with path.open(encoding="utf-8") as f:
        for raw in f:
            if not raw.strip():
                continue
            total += 1
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                invalid += 1
                continue
            row = _replay_row(obj)
            if row is not None:
                rows.append(row)
    return ReplayReport(total_rows=total, invalid_json_lines=invalid, replay_rows=rows)


def render_report(report: ReplayReport, *, clone_k: int = 5, epoch_limit: int = 5) -> str:
    rows = report.replay_rows
    coldkey_rows = sum(1 for r in rows if r.coldkey)
    blockers = decision_data_blockers(report)
    gaps = decision_data_gaps(report)
    lines = [
        "Sybil/Pareto replay analysis",
        f"rows_total={report.total_rows}",
        f"rows_replayable={len(rows)}",
        f"rows_with_coldkey={coldkey_rows}",
        f"invalid_json_lines={report.invalid_json_lines}",
        f"decision_data_blockers={','.join(blockers) if blockers else 'none'}",
        f"decision_data_gaps={','.join(gaps) if gaps else 'none'}",
        f"decision_ready={'no' if blockers else 'yes'}",
    ]
    if not rows:
        lines.append("No replayable full-export rows found.")
        return "\n".join(lines)
    if coldkey_rows == 0:
        lines.append("coldkey_note=no coldkeys in export; coldkey dedup assumes one coldkey per UID")

    epochs = _epochs(rows)
    selected = sorted(epochs.items())[-max(0, int(epoch_limit)) :]
    lines.append(f"epochs_total={len(epochs)}")
    lines.append(f"epochs_rendered={len(selected)}")

    epoch_results = []
    for block, epoch_rows in selected:
        base = replay_epoch(epoch_rows, name="base", identical_dedup=True, coldkey_dedup=True)
        scenarios = [
            base,
            replay_epoch(epoch_rows, name="no_identical_dedup", identical_dedup=False, coldkey_dedup=True),
            replay_epoch(epoch_rows, name="no_coldkey_dedup", identical_dedup=True, coldkey_dedup=False),
            replay_epoch(epoch_rows, name="no_dedup", identical_dedup=False, coldkey_dedup=False),
        ]
        exact = clone_pressure(epoch_rows, clone_k=clone_k, rewrite=False)
        rewritten = clone_pressure(epoch_rows, clone_k=clone_k, rewrite=True)
        epoch_results.append((block, epoch_rows, scenarios, exact, rewritten))

    exact_pressures = [r[3] for r in epoch_results]
    rewritten_pressures = [r[4] for r in epoch_results]
    lines.append(f"clone_k={max(0, int(clone_k))}")
    lines.append(_pressure_summary_line("exact_clone_extra_share", exact_pressures))
    lines.append(_pressure_summary_line("rewritten_clone_extra_share", rewritten_pressures))
    lines.append(_pressure_summary_line("rewritten_clone_group_share", rewritten_pressures, field="group_share"))

    for block, epoch_rows, scenarios, exact, rewritten in epoch_results:
        lines.append(f"epoch={block} rows={len(epoch_rows)}")
        for outcome in scenarios:
            lines.append("  " + _outcome_line(outcome))

        if exact is not None:
            lines.append("  " + _clone_line("exact_clone", exact, clone_k=clone_k))
        if rewritten is not None:
            lines.append("  " + _clone_line("rewritten_clone", rewritten, clone_k=clone_k))
    return "\n".join(lines)


def replay_epoch(
    rows: list[ReplayRow],
    *,
    name: str,
    identical_dedup: bool,
    coldkey_dedup: bool,
) -> ReplayOutcome:
    aggregate: dict[int, list[ScoredEntry]] = {}
    identical_dropped = 0
    for theorem_rows in _by_theorem(rows).values():
        entries = [r.entry for r in theorem_rows]
        if identical_dedup:
            entries, dropped = dedup_identical_submissions(entries, lambda e: e.submission_fp)
            identical_dropped += dropped
        for entry in entries:
            aggregate.setdefault(entry.uid, []).append(entry)

    scored = _merge_uid_entries(aggregate)
    coldkey_dropped = 0
    if coldkey_dedup and scored:
        coldkeys = _coldkeys_by_uid(rows)
        scored, coldkey_dropped = dedup_coldkeys(scored, lambda uid: coldkeys.get(uid, f"uid:{uid}"))

    weights = pareto_weights(scored)
    return ReplayOutcome(
        name=name,
        entries_weighted=len(weights),
        identical_dropped=identical_dropped,
        coldkey_dropped=coldkey_dropped,
        weights=weights,
    )


def clone_pressure(rows: list[ReplayRow], *, clone_k: int, rewrite: bool) -> ClonePressure | None:
    if clone_k <= 0 or not rows:
        return None

    base = replay_epoch(rows, name="base", identical_dedup=True, coldkey_dedup=True)
    source_uid = base.top_uid
    if source_uid is None:
        return None

    source_rows = [r for r in rows if r.uid == source_uid]
    if not source_rows:
        return None

    next_uid = max(r.uid for r in rows) + 1
    clone_uids = tuple(range(next_uid, next_uid + clone_k))
    clones: list[ReplayRow] = []
    for clone_uid in clone_uids:
        for row in source_rows:
            entry = replace(row.entry, uid=clone_uid)
            if rewrite:
                entry = replace(entry, submission_fp=f"{entry.submission_fp}:rewrite:{clone_uid}")
            clones.append(replace(row, uid=clone_uid, coldkey=f"clone:{clone_uid}", entry=entry))

    outcome = replay_epoch(
        [*rows, *clones],
        name="rewritten_clone" if rewrite else "exact_clone",
        identical_dedup=True,
        coldkey_dedup=True,
    )
    group = (source_uid, *clone_uids)
    base_share = base.weights.get(source_uid, 0.0)
    group_share = sum(outcome.weights.get(uid, 0.0) for uid in group)
    return ClonePressure(
        source_uid=source_uid,
        base_share=base_share,
        group_share=group_share,
        extra_share=group_share - base_share,
        outcome=outcome,
    )


def decision_ready(report: ReplayReport) -> bool:
    return not decision_data_blockers(report)


def decision_data_gaps(report: ReplayReport) -> list[str]:
    rows = report.replay_rows
    epochs = _epochs(rows)
    gaps: list[str] = []
    if report.invalid_json_lines:
        gaps.append(f"invalid_json_lines={report.invalid_json_lines}")
    if missing := max(0, MIN_DECISION_REPLAYABLE_ROWS - len(rows)):
        gaps.append(f"replayable_rows+{missing}")
    if missing := max(0, MIN_DECISION_EPOCHS - len(epochs)):
        gaps.append(f"epochs+{missing}")
    if missing := max(0, MIN_DECISION_UIDS - len({r.uid for r in rows})):
        gaps.append(f"uids+{missing}")
    if missing := max(0, MIN_DECISION_THEOREMS - len({r.theorem_id for r in rows})):
        gaps.append(f"theorems+{missing}")
    coldkey_rows = sum(1 for r in rows if r.coldkey)
    if missing := len(rows) - coldkey_rows:
        gaps.append(f"coldkey_rows+{missing}")
    return gaps


def decision_data_blockers(report: ReplayReport) -> list[str]:
    rows = report.replay_rows
    epochs = _epochs(rows)
    blockers: list[str] = []
    if report.invalid_json_lines:
        blockers.append(f"invalid_json_lines={report.invalid_json_lines}")
    if len(rows) < MIN_DECISION_REPLAYABLE_ROWS:
        blockers.append(f"replayable_rows<{MIN_DECISION_REPLAYABLE_ROWS}")
    if len(epochs) < MIN_DECISION_EPOCHS:
        blockers.append(f"epochs<{MIN_DECISION_EPOCHS}")
    if len({r.uid for r in rows}) < MIN_DECISION_UIDS:
        blockers.append(f"uids<{MIN_DECISION_UIDS}")
    if len({r.theorem_id for r in rows}) < MIN_DECISION_THEOREMS:
        blockers.append(f"theorems<{MIN_DECISION_THEOREMS}")
    coldkey_rows = sum(1 for r in rows if r.coldkey)
    if coldkey_rows < len(rows):
        blockers.append("coldkey_coverage<100%")
    return blockers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "jsonl",
        nargs="?",
        type=Path,
        help="Full training export JSONL. Defaults to LEMMA_TRAINING_EXPORT_JSONL.",
    )
    parser.add_argument("--clone-k", type=int, default=5, help="Number of coordinated clone UIDs to simulate.")
    parser.add_argument("--epochs", type=int, default=5, help="Number of latest block groups to print.")
    parser.add_argument("--proof-weight", type=float, default=DEFAULT_PROOF_WEIGHT, help="Legacy; ignored.")
    parser.add_argument(
        "--require-decision-ready",
        action="store_true",
        help="Exit 2 unless the export has enough clean replay data for a sybil/Pareto policy decision.",
    )
    args = parser.parse_args(argv)

    path = args.jsonl or _env_export_path()
    if path is None:
        parser.error("pass a JSONL path or set LEMMA_TRAINING_EXPORT_JSONL")
    if not path.is_file():
        parser.error(f"not a file: {path}")

    report = load_report(path, proof_weight=args.proof_weight)
    print(render_report(report, clone_k=max(0, args.clone_k), epoch_limit=max(0, args.epochs)))
    if args.require_decision_ready and not decision_ready(report):
        return 2
    return 0


def _replay_row(obj: Any) -> ReplayRow | None:
    if not isinstance(obj, dict):
        return None
    uid = _as_int(obj.get("uid"))
    block = _as_int(obj.get("block"))
    theorem_id = str(obj.get("theorem_id") or "")
    proof = obj.get("proof_script")
    if uid is None or block is None or not theorem_id or not isinstance(proof, str):
        return None

    theorem_key = str(obj.get("theorem_statement") or theorem_id)
    fp = submission_fingerprint(theorem_key, proof)
    return ReplayRow(
        block=block,
        theorem_id=theorem_id,
        uid=uid,
        coldkey=_optional_str(obj.get("coldkey") or obj.get("coldkey_ss58")),
        entry=ScoredEntry(uid=uid, score=1.0, cost=0, submission_fp=fp),
    )


def _merge_uid_entries(uid_groups: dict[int, list[ScoredEntry]]) -> list[ScoredEntry]:
    merged: list[ScoredEntry] = []
    for uid, entries in uid_groups.items():
        if len(entries) == 1:
            merged.append(entries[0])
            continue
        score = sum(e.score for e in entries) / len(entries)
        cost = int(round(sum(e.cost for e in entries) / len(entries)))
        merged.append(ScoredEntry(uid=uid, score=score, cost=cost))
    return merged


def _epochs(rows: list[ReplayRow]) -> dict[int, list[ReplayRow]]:
    grouped: dict[int, list[ReplayRow]] = {}
    for row in rows:
        grouped.setdefault(row.block, []).append(row)
    return grouped


def _by_theorem(rows: list[ReplayRow]) -> dict[str, list[ReplayRow]]:
    grouped: dict[str, list[ReplayRow]] = {}
    for row in rows:
        grouped.setdefault(row.theorem_id, []).append(row)
    return grouped


def _coldkeys_by_uid(rows: list[ReplayRow]) -> dict[int, str]:
    coldkeys: dict[int, str] = {}
    for row in rows:
        if row.coldkey:
            coldkeys.setdefault(row.uid, row.coldkey)
        else:
            coldkeys.setdefault(row.uid, f"uid:{row.uid}")
    return coldkeys


def _outcome_line(outcome: ReplayOutcome) -> str:
    top_uid = "none" if outcome.top_uid is None else str(outcome.top_uid)
    return (
        f"{outcome.name}: weighted_uids={outcome.entries_weighted} top_uid={top_uid} "
        f"top_weight={outcome.top_weight:.4f} identical_dropped={outcome.identical_dropped} "
        f"coldkey_dropped={outcome.coldkey_dropped}"
    )


def _clone_line(name: str, pressure: ClonePressure, *, clone_k: int) -> str:
    return (
        f"{name}_k={clone_k}: source_uid={pressure.source_uid} "
        f"base_share={pressure.base_share:.4f} group_share={pressure.group_share:.4f} "
        f"extra_share={pressure.extra_share:.4f} identical_dropped={pressure.outcome.identical_dropped} "
        f"coldkey_dropped={pressure.outcome.coldkey_dropped}"
    )


def _pressure_summary_line(name: str, pressures: list[ClonePressure | None], *, field: str = "extra_share") -> str:
    values = [float(getattr(p, field)) for p in pressures if p is not None]
    if not values:
        return f"summary_{name}: n=0"
    return f"summary_{name}: n={len(values)} max={max(values):.4f} mean={sum(values) / len(values):.4f}"


def _env_export_path() -> Path | None:
    raw = os.environ.get("LEMMA_TRAINING_EXPORT_JSONL", "").strip()
    return Path(raw).expanduser() if raw else None


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    raise SystemExit(main())
