"""Manual Formal Conjectures campaign registry helpers."""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from lemma.problems.base import Problem

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
    reward_label: str
    type_expr: str
    challenge_full: str
    submission_stub: str
    lean_toolchain: str
    mathlib_rev: str
    bounty_note: str = ""
    accepted_solver_uid: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FormalCampaign:
        challenge = _required_text(data, "challenge_full")
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
            reward_label=_required_text(data, "reward_label"),
            type_expr=_required_text(data, "type_expr"),
            challenge_full=challenge,
            submission_stub=str(data.get("submission_stub") or challenge).strip() + "\n",
            lean_toolchain=_required_text(data, "lean_toolchain"),
            mathlib_rev=_required_text(data, "mathlib_rev"),
            bounty_note=str(data.get("bounty_note") or "").strip(),
            accepted_solver_uid=_optional_int(data.get("accepted_solver_uid")),
        )

    def to_problem(self) -> Problem:
        return Problem(
            id=f"bounty/{self.id}",
            theorem_name=self.declaration.rsplit(".", 1)[-1],
            type_expr=self.type_expr,
            split="bounty",
            lean_toolchain=self.lean_toolchain,
            mathlib_rev=self.mathlib_rev,
            imports=("Mathlib",),
            extra={
                "source_lane": "bounty",
                "title": self.title,
                "difficulty": "bounty",
                "source_url": self.source_url,
                "reward_label": self.reward_label,
                "challenge_full": self.challenge_full,
                "submission_stub": self.submission_stub,
            },
        )


@dataclass(frozen=True)
class CampaignAcceptance:
    campaign_id: str
    solver_hotkey: str
    proof_sha256: str
    accepted_unix: int
    solver_uid: int | None = None
    reward_mode: str = CAMPAIGN_REWARD_MODE

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CampaignAcceptance:
        return cls(
            campaign_id=_required_text(data, "campaign_id"),
            solver_hotkey=_required_text(data, "solver_hotkey"),
            proof_sha256=_sha256_or_pending(data.get("proof_sha256")),
            accepted_unix=int(data["accepted_unix"]),
            solver_uid=_optional_int(data.get("solver_uid")),
            reward_mode=str(data.get("reward_mode") or CAMPAIGN_REWARD_MODE),
        )

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":")) + "\n"


def default_campaign_registry_path() -> Path:
    return Path(__file__).resolve().with_name("formal_conjectures_campaigns.json")


def default_bounty_package_dir() -> Path:
    return Path.home() / ".lemma" / "bounty-packages"


def default_campaign_acceptance_ledger_path() -> Path:
    return Path.home() / ".lemma" / "campaign-acceptance-ledger.jsonl"


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


def campaign_by_id(campaign_id: str, path: Path | None = None) -> FormalCampaign:
    for campaign in load_campaigns(path):
        if campaign.id == campaign_id:
            return campaign
    raise KeyError(campaign_id)


def proof_sha256(proof_script: str) -> str:
    proof = proof_script.strip() + "\n"
    return hashlib.sha256(proof.encode("utf-8")).hexdigest()


def bounty_signature_message(campaign: FormalCampaign, proof_hash: str) -> bytes:
    return f"lemma-bounty-v1:{campaign.id}:{proof_hash}".encode()


def build_bounty_package(
    *,
    campaign: FormalCampaign,
    proof_script: str,
    solver_hotkey: str,
    signature_hex: str,
    verify_reason: str,
    build_seconds: float,
    created_unix: int | None = None,
) -> dict[str, Any]:
    proof_hash = proof_sha256(proof_script)
    return {
        "schema": "lemma_bounty_proof_package_v1",
        "campaign": {
            "id": campaign.id,
            "title": campaign.title,
            "source_url": campaign.source_url,
            "upstream_repo": campaign.upstream_repo,
            "upstream_commit": campaign.upstream_commit,
            "lean_file": campaign.lean_file,
            "declaration": campaign.declaration,
            "statement_sha256": campaign.statement_sha256,
            "reward_label": campaign.reward_label,
        },
        "solver": {
            "hotkey": solver_hotkey,
            "signature": signature_hex,
            "signature_message": bounty_signature_message(campaign, proof_hash).decode("utf-8"),
        },
        "proof": {
            "proof_sha256": proof_hash,
            "proof_script": proof_script.strip() + "\n",
            "verify_reason": verify_reason,
            "build_seconds": float(build_seconds),
        },
        "created_unix": int(time.time() if created_unix is None else created_unix),
        "reward_mode": CAMPAIGN_REWARD_MODE,
    }


def write_bounty_package(package_dir: Path | None, package: dict[str, Any]) -> Path:
    out_dir = package_dir or default_bounty_package_dir()
    campaign = package["campaign"]["id"]
    proof_hash = package["proof"]["proof_sha256"][:16]
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{campaign}-{proof_hash}.json"
    path.write_text(json.dumps(package, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path


def load_campaign_acceptances(path: Path | None = None) -> list[CampaignAcceptance]:
    return [CampaignAcceptance.from_dict(row) for row in _read_jsonl(path or default_campaign_acceptance_ledger_path())]


def public_campaigns_payload(
    campaigns: list[FormalCampaign],
    *,
    acceptances: list[CampaignAcceptance] | None = None,
    generated_unix: int | None = None,
) -> dict[str, Any]:
    accepted_by_campaign = {row.campaign_id: row for row in acceptances or []}
    public = [
        _public_campaign_row(campaign, accepted_by_campaign.get(campaign.id))
        for campaign in campaigns
        if campaign.status in {"planned", "open", "accepted", "paid"}
    ]
    return {
        "schema_version": 1,
        "generated_unix": int(time.time() if generated_unix is None else generated_unix),
        "reward_mode": CAMPAIGN_REWARD_MODE,
        "campaigns": public,
    }


def _public_campaign_row(campaign: FormalCampaign, acceptance: CampaignAcceptance | None) -> dict[str, Any]:
    status = campaign.status if acceptance is None or campaign.status == "paid" else "accepted"
    row: dict[str, Any] = {
        "id": campaign.id,
        "title": campaign.title,
        "status": status,
        "source_url": campaign.source_url,
        "upstream_repo": campaign.upstream_repo,
        "upstream_commit": campaign.upstream_commit,
        "lean_file": campaign.lean_file,
        "declaration": campaign.declaration,
        "statement_sha256": campaign.statement_sha256,
        "reward_label": campaign.reward_label,
    }
    if acceptance is not None and status in {"accepted", "paid"}:
        accepted: dict[str, Any] = {
            "solver_hotkey": acceptance.solver_hotkey,
            "accepted_unix": acceptance.accepted_unix,
            "reward_status": status,
        }
        if acceptance.solver_uid is not None:
            accepted["solver_uid"] = acceptance.solver_uid
        row["accepted"] = accepted
    return row


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
    solver_hotkey: str,
    proof_sha256: str,
    solver_uid: int | None = None,
) -> CampaignAcceptance:
    return CampaignAcceptance(
        campaign_id=campaign_id,
        solver_hotkey=solver_hotkey,
        proof_sha256=proof_sha256,
        accepted_unix=int(time.time()),
        solver_uid=None if solver_uid is None else int(solver_uid),
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
