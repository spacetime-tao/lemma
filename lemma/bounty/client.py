"""Client-side bounty registry, verification, packaging, and submission."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import httpx

from lemma import __version__
from lemma.common.config import LemmaSettings
from lemma.lean.problem_codec import problem_from_payload
from lemma.lean.submission_policy import VALID_SUBMISSION_POLICIES
from lemma.problems.base import Problem

BOUNTY_SUBMISSION_SCHEMA_VERSION = 1
BOUNTY_SUBMISSION_MAGIC = b"LemmaBountySubmissionV1"
BOUNTY_SUBMISSIONS_PATH = "/v1/bounty-submissions"


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
    if int(payload.get("schema_version", 0)) != 1:
        raise BountyError("bounty registry schema_version must be 1")
    rows = payload.get("bounties")
    if not isinstance(rows, list):
        raise BountyError("bounty registry must contain a bounties list")
    return BountyRegistry(
        schema_version=1,
        bounties=tuple(Bounty.from_payload(row) for row in rows),
        sha256=digest,
    )


def fetch_registry(settings: LemmaSettings) -> BountyRegistry:
    raw = _read_registry_bytes(settings.bounty_registry_url, float(settings.bounty_http_timeout_s))
    return load_registry(raw, settings.bounty_registry_sha256_expected)


def proof_sha256(proof_script: str) -> str:
    return hashlib.sha256(proof_script.encode("utf-8")).hexdigest()


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


def bounty_submission_message(payload: dict[str, Any]) -> bytes:
    signed = {
        "schema_version": int(payload["schema_version"]),
        "bounty_id": str(payload["bounty_id"]),
        "registry_sha256": str(payload["registry_sha256"]),
        "proof_sha256": str(payload["proof_sha256"]),
        "submitter_hotkey_ss58": str(payload["submitter_hotkey_ss58"]),
        "payout_ss58": str(payload["payout_ss58"]),
        "lemma_version": str(payload["lemma_version"]),
    }
    return BOUNTY_SUBMISSION_MAGIC + b"\n" + _canonical_json(signed).encode("utf-8")


def build_submission_package(
    settings: LemmaSettings,
    *,
    registry: BountyRegistry,
    bounty: Bounty,
    proof_script: str,
    wallet_cold: str | None,
    wallet_hot: str | None,
    payout_ss58: str,
) -> dict[str, Any]:
    import bittensor as bt

    wallet = bt.Wallet(name=wallet_cold or settings.wallet_cold, hotkey=wallet_hot or settings.wallet_hot)
    submitter = wallet.hotkey.ss58_address
    payload: dict[str, Any] = {
        "schema_version": BOUNTY_SUBMISSION_SCHEMA_VERSION,
        "bounty_id": bounty.id,
        "registry_sha256": registry.sha256,
        "proof_script": proof_script,
        "proof_sha256": proof_sha256(proof_script),
        "submitter_hotkey_ss58": submitter,
        "payout_ss58": payout_ss58.strip(),
        "lemma_version": __version__,
    }
    if not payload["payout_ss58"]:
        raise BountyError("--payout is required")
    signature = wallet.hotkey.sign(bounty_submission_message(payload))
    payload["signature_hex"] = signature.hex()
    return payload


def submit_submission_package(settings: LemmaSettings, package: dict[str, Any]) -> dict[str, Any]:
    url = settings.bounty_api_url.rstrip("/") + BOUNTY_SUBMISSIONS_PATH
    try:
        with httpx.Client(timeout=float(settings.bounty_http_timeout_s), follow_redirects=False) as client:
            response = client.post(url, json=package)
    except httpx.HTTPError as e:
        raise BountyError(f"could not submit bounty proof: {e}") from e

    text = response.text[:1000]
    try:
        data = response.json()
    except ValueError:
        data = {"status_code": response.status_code, "body": text}

    if response.status_code in (200, 201, 202, 409):
        return data if isinstance(data, dict) else {"response": data}
    raise BountyError(f"bounty API rejected submission ({response.status_code}): {text}")
