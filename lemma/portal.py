"""HTTP portal for wallet-submitted miner proofs."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from urllib.request import urlopen

from bittensor_wallet import Keypair

from lemma.commitments import build_proof_commitment, canonical_json, proof_sha256
from lemma.common.config import LemmaSettings
from lemma.common.subtensor import get_subtensor
from lemma.lean.sandbox import VerifyResult
from lemma.lean.verify_runner import run_lean_verify
from lemma.lifecycle import target_phase
from lemma.problems.base import Problem
from lemma.problems.factory import get_problem_source, resolve_problem
from lemma.problems.known_theorems import known_theorems_manifest_sha256
from lemma.protocol import LemmaChallenge

PORTAL_SUBMISSION_SCHEMA = "lemma_portal_submission_v1"
PORTAL_STATE_SCHEMA = "lemma_portal_state_v1"
PORTAL_SIGNING_DOMAIN = "lemma:portal:v1"
_MAX_BODY_BYTES = 2_000_000


class PortalError(ValueError):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class PortalCandidate:
    schema: str
    netuid: int
    miner_hotkey: str
    target_id: str
    manifest_sha256: str
    theorem_statement_sha256: str
    proof_sha256: str
    proof_nonce: str
    commitment_hash: str
    commitment_block: int
    commit_cutoff_block: int
    reveal_block: int
    submitted_unix: int
    signature: str
    proof_script: str | None = None
    verify_reason: str | None = None
    build_seconds: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PortalCandidate:
        return cls(
            schema=_text(data, "schema"),
            netuid=_int(data, "netuid"),
            miner_hotkey=_text(data, "miner_hotkey"),
            target_id=_text(data, "target_id"),
            manifest_sha256=_text(data, "manifest_sha256"),
            theorem_statement_sha256=_text(data, "theorem_statement_sha256"),
            proof_sha256=_text(data, "proof_sha256"),
            proof_nonce=_text(data, "proof_nonce"),
            commitment_hash=_text(data, "commitment_hash"),
            commitment_block=_int(data, "commitment_block"),
            commit_cutoff_block=_int(data, "commit_cutoff_block"),
            reveal_block=_int(data, "reveal_block"),
            submitted_unix=_int(data, "submitted_unix"),
            signature=_text(data, "signature"),
            proof_script=_optional_proof_script(data, "proof_script"),
            verify_reason=_optional_text(data, "verify_reason"),
            build_seconds=_optional_float(data, "build_seconds"),
        )

    def header(self) -> dict[str, Any]:
        return portal_candidate_header(asdict(self))

    def to_synapse(self, problem: Problem, *, poll_id: str) -> LemmaChallenge:
        return LemmaChallenge(
            theorem_id=problem.id,
            theorem_statement=problem.challenge_source(),
            imports=list(problem.imports),
            lean_toolchain=problem.lean_toolchain,
            mathlib_rev=problem.mathlib_rev,
            poll_id=poll_id,
            proof_script=self.proof_script,
            proof_nonce=self.proof_nonce,
            commitment_hash=self.commitment_hash,
        )


def normalize_proof_script(proof_script: str) -> str:
    proof = str(proof_script or "").strip() + "\n"
    if not proof.strip():
        raise PortalError("proof_script is empty")
    return proof


def default_portal_db_path() -> Path:
    return Path.home() / ".lemma" / "portal.sqlite3"


def resolved_portal_db_path(path: Path | None) -> Path:
    return path or default_portal_db_path()


def portal_candidate_header(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": _text(data, "schema"),
        "netuid": _int(data, "netuid"),
        "miner_hotkey": _text(data, "miner_hotkey"),
        "target_id": _text(data, "target_id"),
        "manifest_sha256": _text(data, "manifest_sha256"),
        "theorem_statement_sha256": _text(data, "theorem_statement_sha256"),
        "proof_sha256": _text(data, "proof_sha256"),
        "proof_nonce": _text(data, "proof_nonce"),
        "commitment_hash": _text(data, "commitment_hash"),
        "commitment_block": _int(data, "commitment_block"),
        "commit_cutoff_block": _int(data, "commit_cutoff_block"),
        "reveal_block": _int(data, "reveal_block"),
        "submitted_unix": _int(data, "submitted_unix"),
    }


def portal_signing_message(header: dict[str, Any]) -> str:
    return f"{PORTAL_SIGNING_DOMAIN}:{canonical_json(header)}"


def portal_candidate_signature_ok(candidate: PortalCandidate) -> bool:
    try:
        return Keypair(ss58_address=candidate.miner_hotkey).verify(
            portal_signing_message(candidate.header()),
            candidate.signature,
        )
    except Exception:
        return False


def validate_submission_payload(
    settings: LemmaSettings,
    data: dict[str, Any],
    *,
    require_registered: bool = True,
    require_onchain_commitment: bool = False,
    subtensor: Any | None = None,
) -> tuple[Problem, PortalCandidate]:
    raw = dict(data)
    raw["proof_script"] = normalize_proof_script(_text(raw, "proof_script"))
    if len(raw["proof_script"]) > int(settings.synapse_max_proof_chars):
        raise PortalError("proof_script too large", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
    candidate = PortalCandidate.from_dict(raw)
    if candidate.schema != PORTAL_SUBMISSION_SCHEMA:
        raise PortalError("unsupported portal submission schema")
    if candidate.netuid != settings.netuid:
        raise PortalError("netuid mismatch")
    if candidate.commitment_block > candidate.commit_cutoff_block:
        raise PortalError("commitment_block is after commit_cutoff_block")
    problem = resolve_problem(settings, candidate.target_id)
    manifest_sha = known_theorems_manifest_sha256(settings.known_theorems_manifest_path)
    if candidate.manifest_sha256 != manifest_sha:
        raise PortalError("manifest_sha256 mismatch")
    if candidate.theorem_statement_sha256 != problem.theorem_statement_sha256():
        raise PortalError("theorem_statement_sha256 mismatch")
    if candidate.proof_sha256 != proof_sha256(candidate.proof_script or ""):
        raise PortalError("proof_sha256 mismatch")
    expected = build_proof_commitment(
        netuid=settings.netuid,
        miner_hotkey=candidate.miner_hotkey,
        manifest_sha256=manifest_sha,
        problem=problem,
        proof_hash=candidate.proof_sha256,
        nonce=candidate.proof_nonce,
    )
    if candidate.commitment_hash != expected.commitment_hash:
        raise PortalError("commitment_hash mismatch")
    if not portal_candidate_signature_ok(candidate):
        raise PortalError("bad submission signature", HTTPStatus.FORBIDDEN)
    active_subtensor = subtensor or get_subtensor(settings)
    if require_registered:
        uid = active_subtensor.get_uid_for_hotkey_on_subnet(
            candidate.miner_hotkey,
            settings.netuid,
        )
        if uid is None:
            raise PortalError("miner_hotkey is not registered", HTTPStatus.FORBIDDEN)
    if require_onchain_commitment:
        commitments = active_subtensor.get_all_commitments(settings.netuid, block=candidate.commitment_block)
        if not isinstance(commitments, dict) or commitments.get(candidate.miner_hotkey) != expected.payload_text:
            raise PortalError("matching on-chain commitment not found", HTTPStatus.FORBIDDEN)
    return problem, candidate


def init_portal_db(path: Path | None) -> Path:
    db_path = resolved_portal_db_path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                target_id TEXT NOT NULL,
                miner_hotkey TEXT NOT NULL,
                proof_sha256 TEXT NOT NULL,
                proof_nonce TEXT NOT NULL,
                schema TEXT NOT NULL,
                netuid INTEGER NOT NULL,
                manifest_sha256 TEXT NOT NULL,
                theorem_statement_sha256 TEXT NOT NULL,
                commitment_hash TEXT NOT NULL,
                commitment_block INTEGER NOT NULL,
                commit_cutoff_block INTEGER NOT NULL,
                reveal_block INTEGER NOT NULL,
                submitted_unix INTEGER NOT NULL,
                signature TEXT NOT NULL,
                proof_script TEXT NOT NULL,
                verify_passed INTEGER NOT NULL,
                verify_reason TEXT NOT NULL,
                build_seconds REAL NOT NULL,
                PRIMARY KEY (target_id, miner_hotkey, proof_sha256, proof_nonce)
            )
            """,
        )
    return db_path


def save_verified_submission(path: Path | None, candidate: PortalCandidate, result: VerifyResult) -> None:
    if not result.passed:
        raise PortalError(f"Lean rejected this proof: {result.reason}")
    db_path = init_portal_db(path)
    with sqlite3.connect(db_path) as db:
        db.execute(
            """
            INSERT OR REPLACE INTO submissions (
                target_id, miner_hotkey, proof_sha256, proof_nonce, schema, netuid,
                manifest_sha256, theorem_statement_sha256, commitment_hash, commitment_block,
                commit_cutoff_block, reveal_block, submitted_unix, signature, proof_script,
                verify_passed, verify_reason, build_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate.target_id,
                candidate.miner_hotkey,
                candidate.proof_sha256,
                candidate.proof_nonce,
                candidate.schema,
                candidate.netuid,
                candidate.manifest_sha256,
                candidate.theorem_statement_sha256,
                candidate.commitment_hash,
                candidate.commitment_block,
                candidate.commit_cutoff_block,
                candidate.reveal_block,
                candidate.submitted_unix,
                candidate.signature,
                candidate.proof_script,
                1,
                result.reason,
                float(result.build_seconds),
            ),
        )


def load_portal_candidates(path: Path | None, *, current_block: int | None = None) -> list[dict[str, Any]]:
    db_path = init_portal_db(path)
    rows: list[dict[str, Any]] = []
    with sqlite3.connect(db_path) as db:
        db.row_factory = sqlite3.Row
        for row in db.execute(
            """
            SELECT * FROM submissions
            WHERE verify_passed = 1
            ORDER BY commitment_block ASC, submitted_unix ASC
            """,
        ):
            data = dict(row)
            include_proof = current_block is not None and int(current_block) >= int(data["reveal_block"])
            if not include_proof:
                data.pop("proof_script", None)
            data.pop("verify_passed", None)
            rows.append(data)
    return rows


def portal_candidates_response(settings: LemmaSettings) -> dict[str, Any]:
    current_block: int | None = None
    try:
        current_block = int(get_subtensor(settings).get_current_block())
    except Exception:
        pass
    return {
        "current_block": current_block,
        "candidates": load_portal_candidates(settings.portal_db_path, current_block=current_block),
    }


def fetch_portal_candidates(
    url: str,
    *,
    current_block: int | None = None,
    timeout_s: float = 10.0,
) -> list[PortalCandidate]:
    candidate_url = _url_with_current_block(url, current_block)
    with urlopen(candidate_url, timeout=timeout_s) as response:  # noqa: S310
        payload = json.loads(response.read().decode("utf-8"))
    candidates = payload.get("candidates") if isinstance(payload, dict) else None
    if not isinstance(candidates, list):
        raise PortalError("portal candidate response is not a candidate list")
    out: list[PortalCandidate] = []
    for row in candidates:
        if isinstance(row, dict) and row.get("proof_script"):
            out.append(PortalCandidate.from_dict(row))
    return out


def portal_state(settings: LemmaSettings) -> dict[str, Any]:
    source = get_problem_source(settings)
    manifest_sha = known_theorems_manifest_sha256(settings.known_theorems_manifest_path)
    try:
        problem = source.sample(seed=0)
    except ValueError:
        problem = None
    current_block: int | None = None
    phase_row: dict[str, Any] | None = None
    try:
        subtensor = get_subtensor(settings)
        current_block = int(subtensor.get_current_block())
        hashes = {p.id: p.theorem_statement_sha256() for p in source.all_problems()}
        from lemma.ledger import matching_solved_ledger

        phase = target_phase(settings, matching_solved_ledger(settings.solved_ledger_path, hashes), current_block)
        phase_row = {
            "name": phase.name,
            "target_start_block": phase.target_start_block,
            "commit_cutoff_block": phase.commit_cutoff_block,
            "reveal_block": phase.reveal_block,
            "current_block": phase.current_block,
            "blocks_until_reveal": phase.blocks_until_reveal,
        }
    except Exception:
        pass
    active = None
    if problem is not None:
        active = {
            "id": problem.id,
            "title": str(problem.extra.get("title") or problem.id),
            "theorem_name": problem.theorem_name,
            "challenge_source": problem.challenge_source(),
            "submission_stub": problem.submission_stub(),
            "imports": list(problem.imports),
            "lean_toolchain": problem.lean_toolchain,
            "mathlib_rev": problem.mathlib_rev,
            "theorem_statement_sha256": problem.theorem_statement_sha256(),
        }
    return {
        "schema": PORTAL_STATE_SCHEMA,
        "netuid": settings.netuid,
        "problem_source": settings.problem_source,
        "manifest_sha256": manifest_sha,
        "current_block": current_block,
        "phase": phase_row,
        "active_target": active,
        "commitment_schema": "lemma_proof_commitment_v1",
        "commitment_prefix": "lemma:v1:",
        "submission_schema": PORTAL_SUBMISSION_SCHEMA,
    }


def verify_candidate_payload(
    settings: LemmaSettings,
    data: dict[str, Any],
) -> tuple[Problem, PortalCandidate, VerifyResult]:
    problem, candidate = validate_submission_payload(settings, data, require_onchain_commitment=True)
    result = run_lean_verify(
        settings,
        verify_timeout_s=settings.lean_verify_timeout_s,
        problem=problem,
        proof_script=candidate.proof_script or "",
    )
    return problem, candidate, result


def run_portal_server(settings: LemmaSettings | None = None) -> None:
    active_settings = settings or LemmaSettings()
    init_portal_db(active_settings.portal_db_path)
    server = _PortalHTTPServer(
        (active_settings.portal_host, active_settings.portal_port),
        _PortalHandler,
        settings=active_settings,
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()


class _PortalHTTPServer(ThreadingHTTPServer):
    def __init__(self, *args: Any, settings: LemmaSettings, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.settings = settings


class _PortalHandler(BaseHTTPRequestHandler):
    server: _PortalHTTPServer

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/portal/v1/state":
            self._write_json(HTTPStatus.OK, portal_state(self.server.settings))
            return
        if parsed.path == "/api/portal/v1/candidates":
            self._write_json(HTTPStatus.OK, portal_candidates_response(self.server.settings))
            return
        self._write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._write_cors_headers()
        self.send_header("content-length", "0")
        self.end_headers()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            data = self._read_json()
            if parsed.path == "/api/portal/v1/verify":
                problem, candidate, result = verify_candidate_payload(self.server.settings, data)
                self._write_json(
                    HTTPStatus.OK,
                    {
                        "target_id": problem.id,
                        "proof_sha256": candidate.proof_sha256,
                        "passed": result.passed,
                        "reason": result.reason,
                        "build_seconds": result.build_seconds,
                        "stderr_tail": result.stderr_tail,
                    },
                )
                return
            if parsed.path == "/api/portal/v1/submissions":
                _problem, candidate, result = verify_candidate_payload(self.server.settings, data)
                save_verified_submission(self.server.settings.portal_db_path, candidate, result)
                self._write_json(
                    HTTPStatus.OK,
                    {
                        "accepted": True,
                        "target_id": candidate.target_id,
                        "proof_sha256": candidate.proof_sha256,
                        "verify_reason": result.reason,
                        "build_seconds": result.build_seconds,
                    },
                )
                return
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
        except PortalError as exc:
            self._write_json(exc.status, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            self._write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def _read_json(self) -> dict[str, Any]:
        raw_len = int(self.headers.get("content-length") or "0")
        if raw_len > _MAX_BODY_BYTES:
            raise PortalError("request body too large", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        try:
            data = json.loads(self.rfile.read(raw_len).decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise PortalError("request body is not valid JSON") from exc
        if not isinstance(data, dict):
            raise PortalError("request body must be a JSON object")
        return data

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
        self.send_response(int(status))
        self.send_header("content-type", "application/json; charset=utf-8")
        self._write_cors_headers()
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_cors_headers(self) -> None:
        self.send_header("access-control-allow-origin", "*")
        self.send_header("access-control-allow-methods", "GET, POST, OPTIONS")
        self.send_header("access-control-allow-headers", "content-type")

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return None


def _url_with_current_block(url: str, current_block: int | None) -> str:
    if current_block is None:
        return url
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query["current_block"] = [str(current_block)]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def _text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if value is None:
        raise PortalError(f"{key} is required")
    text = str(value).strip()
    if not text:
        raise PortalError(f"{key} is required")
    return text


def _optional_text(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_proof_script(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    return normalize_proof_script(str(value))


def _int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if value is None:
        raise PortalError(f"{key} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise PortalError(f"{key} must be an integer") from exc


def _optional_float(data: dict[str, Any], key: str) -> float | None:
    value = data.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise PortalError(f"{key} must be a number") from exc
