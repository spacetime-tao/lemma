"""Manual Formal Conjectures campaign registry helpers."""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

CAMPAIGN_SCHEMA = "lemma_formal_conjectures_campaigns_v1"
CAMPAIGN_REWARD_MODE = "manual_winner_take_all_owner_emission"
CAMPAIGN_STATUSES = frozenset({"planned", "open", "accepted", "paid", "closed"})
_DECL_RE = re.compile(r"\btheorem\s+([A-Za-z_][A-Za-z0-9_'.]*)\b")


@dataclass(frozen=True)
class FormalCampaign:
    id: str
    title: str
    status: str
    source_url: str
    upstream_repo: str
    upstream_commit: str
    lean_file: str
    declaration: str
    statement_sha256: str
    bounty_note: str
    accepted_solver_uid: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FormalCampaign:
        return cls(
            id=_required_text(data, "id"),
            title=_required_text(data, "title"),
            status=_status(data),
            source_url=_required_text(data, "source_url"),
            upstream_repo=_required_text(data, "upstream_repo"),
            upstream_commit=_required_text(data, "upstream_commit"),
            lean_file=_required_text(data, "lean_file"),
            declaration=_required_text(data, "declaration"),
            statement_sha256=_sha256_or_pending(data.get("statement_sha256")),
            bounty_note=_required_text(data, "bounty_note"),
            accepted_solver_uid=_optional_int(data.get("accepted_solver_uid")),
        )


@dataclass(frozen=True)
class CampaignAcceptance:
    campaign_id: str
    solver_uid: int
    solver_hotkey: str
    proof_sha256: str
    accepted_unix: int
    reward_mode: str = CAMPAIGN_REWARD_MODE

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":")) + "\n"


def default_campaign_registry_path() -> Path:
    return Path(__file__).resolve().with_name("formal_conjectures_campaigns.json")


def load_campaigns(path: Path | None = None) -> list[FormalCampaign]:
    registry_path = path or default_campaign_registry_path()
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    return validate_campaign_registry(data)


def validate_campaign_registry(data: dict[str, Any]) -> list[FormalCampaign]:
    if data.get("schema") != CAMPAIGN_SCHEMA:
        raise ValueError(f"campaign registry schema must be {CAMPAIGN_SCHEMA}")
    rows = data.get("campaigns")
    if not isinstance(rows, list):
        raise ValueError("campaigns must be a list")
    campaigns = [FormalCampaign.from_dict(row) for row in rows if isinstance(row, dict)]
    if len(campaigns) != len(rows):
        raise ValueError("campaign rows must be objects")
    seen: set[str] = set()
    for campaign in campaigns:
        if campaign.id in seen:
            raise ValueError(f"duplicate campaign id: {campaign.id}")
        seen.add(campaign.id)
        if campaign.accepted_solver_uid is not None and campaign.status not in {"accepted", "paid", "closed"}:
            raise ValueError(f"campaign {campaign.id} has accepted_solver_uid before acceptance")
    return campaigns


def proof_declares_campaign_theorem(campaign: FormalCampaign, proof_script: str) -> bool:
    """Cheap preflight that the submitted Lean file declares the locked theorem name."""
    wanted = campaign.declaration.rsplit(".", 1)[-1]
    return wanted in _DECL_RE.findall(proof_script)


def append_campaign_acceptance(path: Path, acceptance: CampaignAcceptance) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_ids = {
        str(row.get("campaign_id"))
        for row in _read_jsonl(path)
        if isinstance(row, dict) and str(row.get("campaign_id") or "").strip()
    }
    if acceptance.campaign_id in existing_ids:
        raise ValueError(f"campaign already accepted: {acceptance.campaign_id}")
    with path.open("a", encoding="utf-8") as f:
        f.write(acceptance.to_json_line())


def new_campaign_acceptance(
    *,
    campaign_id: str,
    solver_uid: int,
    solver_hotkey: str,
    proof_sha256: str,
) -> CampaignAcceptance:
    return CampaignAcceptance(
        campaign_id=campaign_id,
        solver_uid=int(solver_uid),
        solver_hotkey=solver_hotkey,
        proof_sha256=proof_sha256,
        accepted_unix=int(time.time()),
    )


def _required_text(data: dict[str, Any], key: str) -> str:
    value = str(data.get(key) or "").strip()
    if not value:
        raise ValueError(f"{key} is required")
    return value


def _status(data: dict[str, Any]) -> str:
    status = _required_text(data, "status")
    if status not in CAMPAIGN_STATUSES:
        raise ValueError(f"invalid campaign status: {status}")
    return status


def _sha256_or_pending(value: object) -> str:
    text = str(value or "").strip()
    if text == "pending":
        return text
    if len(text) != 64 or any(c not in "0123456789abcdef" for c in text):
        raise ValueError("statement_sha256 must be 64 lowercase hex chars or pending")
    return text


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(str(value))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
    return rows
