"""Solved-target ledger helpers."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


def default_solved_ledger_path() -> Path:
    return Path.home() / ".lemma" / "solved-ledger.jsonl"


def resolved_solved_ledger_path(path: Path | None) -> Path:
    return path or default_solved_ledger_path()


@dataclass(frozen=True)
class LedgerSolver:
    uid: int
    hotkey: str | None
    coldkey: str | None
    proof_sha256: str
    verify_reason: str
    build_seconds: float
    proof_script: str | None = None
    proof_nonce: str | None = None
    commitment_hash: str | None = None
    commitment_block: int | None = None
    commit_cutoff_block: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LedgerSolver:
        return cls(
            uid=int(data["uid"]),
            hotkey=_str_or_none(data.get("hotkey")),
            coldkey=_str_or_none(data.get("coldkey")),
            proof_sha256=str(data["proof_sha256"]),
            verify_reason=str(data["verify_reason"]),
            build_seconds=float(data["build_seconds"]),
            proof_script=_proof_script_or_none(data.get("proof_script")),
            proof_nonce=_str_or_none(data.get("proof_nonce")),
            commitment_hash=_str_or_none(data.get("commitment_hash")),
            commitment_block=_int_or_none(data.get("commitment_block")),
            commit_cutoff_block=_int_or_none(data.get("commit_cutoff_block")),
        )


@dataclass(frozen=True)
class SolvedLedgerEntry:
    target_id: str
    solvers: tuple[LedgerSolver, ...]
    accepted_block: int
    accepted_unix: int
    validator_hotkey: str
    lemma_version: str
    theorem_statement_sha256: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SolvedLedgerEntry:
        solvers = data.get("solvers")
        if not solvers:
            solvers = data.get("winners")
        if isinstance(solvers, list) and solvers:
            parsed_solvers = tuple(LedgerSolver.from_dict(row) for row in solvers if isinstance(row, dict))
        else:
            parsed_solvers = (
                LedgerSolver(
                    uid=int(data["winner_uid"]),
                    hotkey=_str_or_none(data.get("winner_hotkey")),
                    coldkey=_str_or_none(data.get("winner_coldkey")),
                    proof_sha256=str(data["proof_sha256"]),
                    verify_reason=str(data["verify_reason"]),
                    build_seconds=float(data["build_seconds"]),
                ),
            )
        if not parsed_solvers:
            raise ValueError("solvers must be non-empty")
        return cls(
            target_id=str(data["target_id"]),
            solvers=parsed_solvers,
            accepted_block=int(data["accepted_block"]),
            accepted_unix=int(data["accepted_unix"]),
            validator_hotkey=str(data["validator_hotkey"]),
            lemma_version=str(data["lemma_version"]),
            theorem_statement_sha256=str(data["theorem_statement_sha256"]),
        )

    @property
    def solver_uids(self) -> tuple[int, ...]:
        return tuple(solver.uid for solver in self.solvers)

    @property
    def proof_sha256(self) -> str:
        return self.solvers[0].proof_sha256

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":")) + "\n"


def _str_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _proof_script_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _int_or_none(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(str(value))


def load_solved_ledger(path: Path | None) -> list[SolvedLedgerEntry]:
    ledger_path = resolved_solved_ledger_path(path)
    if not ledger_path.exists():
        return []
    entries: list[SolvedLedgerEntry] = []
    for lineno, line in enumerate(ledger_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            if not isinstance(data, dict):
                raise ValueError("expected JSON object")
            entries.append(SolvedLedgerEntry.from_dict(data))
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"invalid solved ledger row {ledger_path}:{lineno}: {exc}") from exc
    return entries


def _entry_matches_manifest(entry: SolvedLedgerEntry, theorem_statement_sha256_by_target: Mapping[str, str]) -> bool:
    return theorem_statement_sha256_by_target.get(entry.target_id) == entry.theorem_statement_sha256


def matching_solved_ledger(
    path: Path | None,
    theorem_statement_sha256_by_target: Mapping[str, str],
) -> list[SolvedLedgerEntry]:
    return [
        entry
        for entry in load_solved_ledger(path)
        if _entry_matches_manifest(entry, theorem_statement_sha256_by_target)
    ]


def solved_target_ids(
    path: Path | None,
    theorem_statement_sha256_by_target: Mapping[str, str] | None = None,
) -> set[str]:
    entries = (
        load_solved_ledger(path)
        if theorem_statement_sha256_by_target is None
        else matching_solved_ledger(path, theorem_statement_sha256_by_target)
    )
    return {entry.target_id for entry in entries}


def current_solver_set(
    path: Path | None,
    theorem_statement_sha256_by_target: Mapping[str, str] | None = None,
) -> SolvedLedgerEntry | None:
    entries = (
        load_solved_ledger(path)
        if theorem_statement_sha256_by_target is None
        else matching_solved_ledger(path, theorem_statement_sha256_by_target)
    )
    return entries[-1] if entries else None


def append_solved_ledger_entry(path: Path | None, entry: SolvedLedgerEntry) -> None:
    ledger_path = resolved_solved_ledger_path(path)
    for existing in load_solved_ledger(ledger_path):
        if (
            existing.target_id == entry.target_id
            and existing.theorem_statement_sha256 == entry.theorem_statement_sha256
        ):
            raise ValueError(f"target already solved in ledger: {entry.target_id}")
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as f:
        f.write(entry.to_json_line())


def split_solver_weights(solver_uids: Iterable[int], eligible_uids: set[int]) -> dict[int, float]:
    eligible_solvers = tuple(uid for uid in dict.fromkeys(solver_uids) if uid in eligible_uids)
    if not eligible_solvers:
        return {}
    share = 1.0 / len(eligible_solvers)
    return {uid: share for uid in eligible_solvers}


def active_solver_weights(
    path: Path | None,
    eligible_uids: set[int],
    theorem_statement_sha256_by_target: Mapping[str, str] | None = None,
) -> dict[int, float]:
    solver_set = current_solver_set(path, theorem_statement_sha256_by_target)
    if solver_set is None:
        return {}
    return split_solver_weights(solver_set.solver_uids, eligible_uids)
