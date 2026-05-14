"""Winner-take-all ledger helpers."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


def default_wta_ledger_path() -> Path:
    return Path.home() / ".lemma" / "wta-ledger.jsonl"


def resolved_wta_ledger_path(path: Path | None) -> Path:
    return path or default_wta_ledger_path()


@dataclass(frozen=True)
class WtaWinner:
    uid: int
    hotkey: str | None
    coldkey: str | None
    proof_sha256: str
    verify_reason: str
    build_seconds: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WtaWinner:
        return cls(
            uid=int(data["uid"]),
            hotkey=_str_or_none(data.get("hotkey")),
            coldkey=_str_or_none(data.get("coldkey")),
            proof_sha256=str(data["proof_sha256"]),
            verify_reason=str(data["verify_reason"]),
            build_seconds=float(data["build_seconds"]),
        )


@dataclass(frozen=True)
class WtaLedgerEntry:
    target_id: str
    winners: tuple[WtaWinner, ...]
    accepted_block: int
    accepted_unix: int
    validator_hotkey: str
    lemma_version: str
    theorem_statement_sha256: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WtaLedgerEntry:
        winners = data.get("winners")
        if isinstance(winners, list) and winners:
            parsed_winners = tuple(WtaWinner.from_dict(row) for row in winners if isinstance(row, dict))
        else:
            parsed_winners = (
                WtaWinner(
                    uid=int(data["winner_uid"]),
                    hotkey=_str_or_none(data.get("winner_hotkey")),
                    coldkey=_str_or_none(data.get("winner_coldkey")),
                    proof_sha256=str(data["proof_sha256"]),
                    verify_reason=str(data["verify_reason"]),
                    build_seconds=float(data["build_seconds"]),
                ),
            )
        if not parsed_winners:
            raise ValueError("winners must be non-empty")
        return cls(
            target_id=str(data["target_id"]),
            winners=parsed_winners,
            accepted_block=int(data["accepted_block"]),
            accepted_unix=int(data["accepted_unix"]),
            validator_hotkey=str(data["validator_hotkey"]),
            lemma_version=str(data["lemma_version"]),
            theorem_statement_sha256=str(data["theorem_statement_sha256"]),
        )

    @property
    def winner_uids(self) -> tuple[int, ...]:
        return tuple(winner.uid for winner in self.winners)

    @property
    def winner_uid(self) -> int:
        return self.winners[0].uid

    @property
    def proof_sha256(self) -> str:
        return self.winners[0].proof_sha256

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":")) + "\n"


def _str_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def load_wta_ledger(path: Path | None) -> list[WtaLedgerEntry]:
    ledger_path = resolved_wta_ledger_path(path)
    if not ledger_path.exists():
        return []
    entries: list[WtaLedgerEntry] = []
    for lineno, line in enumerate(ledger_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            if not isinstance(data, dict):
                raise ValueError("expected JSON object")
            entries.append(WtaLedgerEntry.from_dict(data))
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"invalid WTA ledger row {ledger_path}:{lineno}: {exc}") from exc
    return entries


def solved_target_ids(path: Path | None) -> set[str]:
    return {entry.target_id for entry in load_wta_ledger(path)}


def current_champion(path: Path | None) -> WtaLedgerEntry | None:
    entries = load_wta_ledger(path)
    return entries[-1] if entries else None


def append_wta_ledger_entry(path: Path | None, entry: WtaLedgerEntry) -> None:
    ledger_path = resolved_wta_ledger_path(path)
    if entry.target_id in solved_target_ids(ledger_path):
        raise ValueError(f"target already solved in WTA ledger: {entry.target_id}")
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as f:
        f.write(entry.to_json_line())


def split_winner_weights(winner_uids: Iterable[int], eligible_uids: set[int]) -> dict[int, float]:
    eligible_winners = tuple(uid for uid in dict.fromkeys(winner_uids) if uid in eligible_uids)
    if not eligible_winners:
        return {}
    share = 1.0 / len(eligible_winners)
    return {uid: share for uid in eligible_winners}


def champion_weights(path: Path | None, eligible_uids: set[int]) -> dict[int, float]:
    champion = current_champion(path)
    if champion is None:
        return {}
    return split_winner_weights(champion.winner_uids, eligible_uids)
