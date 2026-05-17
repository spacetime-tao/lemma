"""Client-side bounty registry loading and Lean verification."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import httpx

from lemma.common.config import LemmaSettings
from lemma.lean.problem_codec import problem_from_payload
from lemma.lean.submission_policy import VALID_SUBMISSION_POLICIES
from lemma.problems.base import Problem


class BountyError(RuntimeError):
    """Raised when bounty registry, verification, or submission fails."""


@dataclass(frozen=True)
class Bounty:
    id: str
    title: str
    status: str
    reward: str
    deadline: str | None
    terms_url: str | None
    source: dict[str, Any]
    problem: Problem
    kind: str
    submission_policy: str
    target_sha256: str
    policy_version: str
    toolchain_id: str
    escrow: dict[str, Any]

    @classmethod
    def from_payload(cls, row: dict[str, Any]) -> Bounty:
        try:
            problem_payload = row["problem"]
            bounty_id = str(row["id"]).strip()
            title = str(row.get("title") or bounty_id).strip()
        except KeyError as e:
            raise BountyError(f"registry bounty missing required field: {e.args[0]}") from e
        if not bounty_id:
            raise BountyError("registry bounty has empty id")
        source = row.get("source") or {}
        if not isinstance(source, dict):
            raise BountyError(f"registry bounty {bounty_id!r} source must be an object")
        problem = problem_from_payload(problem_payload)
        kind = str(row.get("kind") or "formal_target").strip().lower()
        policy = str(row.get("submission_policy") or problem.extra.get("submission_policy") or "restricted_helpers")
        if policy not in VALID_SUBMISSION_POLICIES:
            raise BountyError(f"registry bounty {bounty_id!r} has unknown submission_policy: {policy}")
        target_hash = target_sha256(problem)
        expected_target_hash = _normalize_sha256_pin(str(row.get("target_sha256") or ""))
        if expected_target_hash and expected_target_hash != target_hash:
            raise BountyError(
                f"registry bounty {bounty_id!r} target_sha256 mismatch: got {target_hash}, "
                f"expected {expected_target_hash}",
            )
        if _formal_conjectures_has_formal_proof(source) and kind != "proof_porting":
            raise BountyError(
                f"registry bounty {bounty_id!r} has Formal Conjectures formal_proof metadata; "
                "use kind=proof_porting instead of a normal bounty",
            )
        policy_version = str(row.get("policy_version") or "bounty-policy-v1").strip()
        toolchain_id = str(row.get("toolchain_id") or problem.lean_toolchain).strip()
        escrow = row.get("escrow") or {}
        if not isinstance(escrow, dict):
            raise BountyError(f"registry bounty {bounty_id!r} escrow must be an object")
        return cls(
            id=bounty_id,
            title=title,
            status=str(row.get("status") or "open").strip().lower(),
            reward=str(row.get("reward") or "").strip(),
            deadline=str(row["deadline"]).strip() if row.get("deadline") else None,
            terms_url=str(row["terms_url"]).strip() if row.get("terms_url") else None,
            source=dict(source),
            problem=problem,
            kind=kind,
            submission_policy=policy,
            target_sha256=target_hash,
            policy_version=policy_version,
            toolchain_id=toolchain_id,
            escrow=dict(escrow),
        )

    @property
    def escrow_bounty_id(self) -> int | None:
        value = self.escrow.get("bounty_id")
        if value in (None, ""):
            return None
        try:
            parsed = int(str(value))
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    @property
    def escrow_contract_address(self) -> str:
        return str(self.escrow.get("contract_address") or "").strip()

    @property
    def escrow_chain_id(self) -> int | None:
        value = self.escrow.get("chain_id")
        if value in (None, ""):
            return None
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return None

    @property
    def escrow_funding_confirmed_block(self) -> int | None:
        value = self.escrow.get("funding_confirmed_block")
        if value in (None, ""):
            return None
        try:
            parsed = int(str(value))
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    @property
    def escrow_funded(self) -> bool:
        return self.escrow.get("funded") is True or self.escrow_funding_confirmed_block is not None

    @property
    def escrow_backed(self) -> bool:
        return bool(
            self.escrow_contract_address
            and self.escrow_bounty_id is not None
            and self.escrow_chain_id
            and self.escrow_funded
        )


@dataclass(frozen=True)
class BountyRegistry:
    schema_version: int
    bounties: tuple[Bounty, ...]
    sha256: str

    def get(self, bounty_id: str) -> Bounty:
        wanted = bounty_id.strip()
        for bounty in self.bounties:
            if bounty.id == wanted:
                return bounty
        raise BountyError(f"unknown bounty id: {bounty_id}")


def _canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _normalize_sha256_pin(value: str | None) -> str | None:
    raw = (value or "").strip().lower()
    if raw.startswith("sha256:"):
        raw = raw.removeprefix("sha256:")
    return raw or None


def target_sha256(problem: Problem) -> str:
    return hashlib.sha256(problem.challenge_source().encode("utf-8")).hexdigest()


def _formal_conjectures_has_formal_proof(source: dict[str, Any]) -> bool:
    fc = source.get("formal_conjectures")
    if not isinstance(fc, dict):
        return False
    if bool(fc.get("formal_proof") or fc.get("has_formal_proof")):
        return True
    return bool(str(fc.get("formal_proof_url") or "").strip())


def _read_registry_bytes(source: str, timeout_s: float) -> bytes:
    src = source.strip()
    if not src:
        raise BountyError("LEMMA_BOUNTY_REGISTRY_URL is empty")
    if src.startswith(("http://", "https://")):
        try:
            response = httpx.get(src, timeout=timeout_s, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise BountyError(f"could not fetch bounty registry: {e}") from e
        return response.content
    if src.startswith("file://"):
        parsed = urlparse(src)
        path = Path(unquote(parsed.path))
    else:
        path = Path(src).expanduser()
    try:
        return path.read_bytes()
    except OSError as e:
        raise BountyError(f"could not read bounty registry {path}: {e}") from e


def load_registry(raw: bytes, expected_sha256: str | None = None) -> BountyRegistry:
    digest = hashlib.sha256(raw).hexdigest()
    expected = _normalize_sha256_pin(expected_sha256)
    if expected and digest != expected:
        raise BountyError(f"bounty registry sha256 mismatch: got {digest}, expected {expected}")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise BountyError(f"bounty registry is not valid UTF-8 JSON: {e}") from e
    if int(payload.get("schema_version", 0)) not in {1, 2}:
        raise BountyError("bounty registry schema_version must be 1 or 2")
    rows = payload.get("bounties")
    if not isinstance(rows, list):
        raise BountyError("bounty registry must contain a bounties list")
    schema_version = int(payload.get("schema_version", 0))
    return BountyRegistry(
        schema_version=schema_version,
        bounties=tuple(Bounty.from_payload(row) for row in rows),
        sha256=digest,
    )


def fetch_registry(settings: LemmaSettings) -> BountyRegistry:
    raw = _read_registry_bytes(settings.bounty_registry_url, float(settings.bounty_http_timeout_s))
    return load_registry(raw, settings.bounty_registry_sha256_expected)


def verify_bounty_proof(settings: LemmaSettings, bounty: Bounty, proof_script: str, *, host_lean: bool = False):
    if host_lean and not settings.allow_host_lean:
        raise BountyError(
            "Host Lean is disabled. Use Docker (default), or set LEMMA_ALLOW_HOST_LEAN=1 for local debugging."
        )
    from lemma.lean.verify_runner import run_lean_verify

    use_docker = not host_lean and settings.lean_use_docker
    eff = settings.model_copy(update={"lean_use_docker": use_docker})
    return run_lean_verify(
        eff,
        verify_timeout_s=settings.lean_verify_timeout_s,
        problem=bounty.problem,
        proof_script=proof_script,
        submission_policy=bounty.submission_policy,
    )
