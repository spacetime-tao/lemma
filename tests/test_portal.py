from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import lemma.portal as portal
import pytest
from bittensor_wallet import Keypair
from lemma.commitments import build_proof_commitment, proof_sha256
from lemma.common.config import LemmaSettings
from lemma.lean.sandbox import VerifyResult
from lemma.problems.factory import get_problem_source
from lemma.problems.known_theorems import known_theorems_manifest_sha256


def _settings(tmp_path: Path) -> LemmaSettings:
    return LemmaSettings(
        _env_file=None,
        solved_ledger_path=tmp_path / "solved-ledger.jsonl",
        portal_db_path=tmp_path / "portal.sqlite3",
    )


def _payload(
    settings: LemmaSettings,
    proof_script: str = "namespace Submission\n-- web proof\n",
    *,
    miner_hotkey: str = "miner-hotkey-1",
    signature: str = "sig",
) -> dict[str, object]:
    problem = get_problem_source(settings).sample(seed=0)
    proof = portal.normalize_proof_script(proof_script)
    proof_hash = proof_sha256(proof)
    nonce = "n" * 64
    manifest_sha = known_theorems_manifest_sha256(settings.known_theorems_manifest_path)
    commitment = build_proof_commitment(
        netuid=settings.netuid,
        miner_hotkey=miner_hotkey,
        manifest_sha256=manifest_sha,
        problem=problem,
        proof_hash=proof_hash,
        nonce=nonce,
    )
    return {
        "schema": portal.PORTAL_SUBMISSION_SCHEMA,
        "netuid": settings.netuid,
        "miner_hotkey": miner_hotkey,
        "target_id": problem.id,
        "manifest_sha256": manifest_sha,
        "theorem_statement_sha256": problem.theorem_statement_sha256(),
        "proof_sha256": proof_hash,
        "proof_nonce": nonce,
        "commitment_hash": commitment.commitment_hash,
        "commitment_block": 10,
        "commit_cutoff_block": 11,
        "reveal_block": 12,
        "submitted_unix": 123,
        "signature": signature,
        "proof_script": proof,
    }


def _commitment_payload(data: dict[str, object]) -> str:
    return f"lemma:v1:{data['commitment_hash']}"


def _signed_payload(settings: LemmaSettings) -> dict[str, object]:
    keypair = Keypair.create_from_uri("//Alice")
    data = _payload(settings, miner_hotkey=keypair.ss58_address)
    header = portal.portal_candidate_header(data)
    data["signature"] = "0x" + keypair.sign(portal.portal_signing_message(header)).hex()
    return data


def test_portal_signing_message_matches_fixture() -> None:
    fixture = json.loads((Path(__file__).parent / "fixtures" / "commitment_v1.json").read_text(encoding="utf-8"))

    assert portal.canonical_json(fixture["portal_header"]) == fixture["portal_header_canonical_json"]
    assert portal.portal_signing_message(fixture["portal_header"]) == fixture["portal_signing_message"]


def test_portal_signature_accepts_wallet_keypair(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    data = _signed_payload(settings)
    candidate = portal.PortalCandidate.from_dict(data)

    assert portal.portal_candidate_signature_ok(candidate)

    tampered = portal.PortalCandidate.from_dict({**data, "submitted_unix": 124})
    assert not portal.portal_candidate_signature_ok(tampered)

    subtensor = SimpleNamespace(
        get_uid_for_hotkey_on_subnet=lambda hotkey, netuid: 1,
        get_all_commitments=lambda netuid, block: {data["miner_hotkey"]: _commitment_payload(data)},
    )
    problem, candidate = portal.validate_submission_payload(
        settings,
        data,
        require_onchain_commitment=True,
        subtensor=subtensor,
    )

    assert candidate.target_id == problem.id


def test_validate_submission_payload_requires_registered_hotkey(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(portal, "portal_candidate_signature_ok", lambda candidate: True)
    subtensor = SimpleNamespace(get_uid_for_hotkey_on_subnet=lambda hotkey, netuid: None)

    with pytest.raises(portal.PortalError, match="not registered"):
        portal.validate_submission_payload(settings, _payload(settings), subtensor=subtensor)


def test_validate_submission_payload_accepts_matching_commitment(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(portal, "portal_candidate_signature_ok", lambda candidate: True)
    subtensor = SimpleNamespace(get_uid_for_hotkey_on_subnet=lambda hotkey, netuid: 1)

    problem, candidate = portal.validate_submission_payload(settings, _payload(settings), subtensor=subtensor)

    assert candidate.target_id == problem.id
    assert candidate.proof_sha256 == proof_sha256(candidate.proof_script or "")


def test_validate_submission_payload_can_require_onchain_commitment(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    data = _payload(settings)
    monkeypatch.setattr(portal, "portal_candidate_signature_ok", lambda candidate: True)
    missing = SimpleNamespace(
        get_uid_for_hotkey_on_subnet=lambda hotkey, netuid: 1,
        get_all_commitments=lambda netuid, block: {},
    )

    with pytest.raises(portal.PortalError, match="matching on-chain commitment"):
        portal.validate_submission_payload(settings, data, require_onchain_commitment=True, subtensor=missing)

    present = SimpleNamespace(
        get_uid_for_hotkey_on_subnet=lambda hotkey, netuid: 1,
        get_all_commitments=lambda netuid, block: {"miner-hotkey-1": _commitment_payload(data)},
    )

    problem, candidate = portal.validate_submission_payload(
        settings,
        data,
        require_onchain_commitment=True,
        subtensor=present,
    )

    assert candidate.target_id == problem.id


def test_verify_candidate_payload_requires_committed_submission(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    data = _payload(settings)
    monkeypatch.setattr(portal, "portal_candidate_signature_ok", lambda candidate: True)
    monkeypatch.setattr(
        portal,
        "get_subtensor",
        lambda settings: SimpleNamespace(
            get_uid_for_hotkey_on_subnet=lambda hotkey, netuid: 1,
            get_all_commitments=lambda netuid, block: {"miner-hotkey-1": _commitment_payload(data)},
        ),
    )
    monkeypatch.setattr(portal, "run_lean_verify", lambda *args, **kwargs: VerifyResult(passed=True, reason="ok"))

    with pytest.raises(portal.PortalError, match="schema is required"):
        portal.verify_candidate_payload(
            settings,
            {"target_id": data["target_id"], "proof_script": data["proof_script"]},
        )

    problem, candidate, result = portal.verify_candidate_payload(settings, data)

    assert candidate.target_id == problem.id
    assert result.passed


def test_load_portal_candidates_hides_proof_until_reveal(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    candidate = portal.PortalCandidate.from_dict(_payload(settings))
    portal.save_verified_submission(
        settings.portal_db_path,
        candidate,
        VerifyResult(passed=True, reason="ok", build_seconds=0.5),
    )

    before_reveal = portal.load_portal_candidates(settings.portal_db_path, current_block=11)
    at_reveal = portal.load_portal_candidates(settings.portal_db_path, current_block=12)

    assert "proof_script" not in before_reveal[0]
    assert at_reveal[0]["proof_script"] == candidate.proof_script


def test_portal_candidates_response_uses_chain_block(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    candidate = portal.PortalCandidate.from_dict(_payload(settings))
    portal.save_verified_submission(
        settings.portal_db_path,
        candidate,
        VerifyResult(passed=True, reason="ok", build_seconds=0.5),
    )
    monkeypatch.setattr(portal, "get_subtensor", lambda settings: SimpleNamespace(get_current_block=lambda: 11))

    response = portal.portal_candidates_response(settings)

    assert response["current_block"] == 11
    assert "proof_script" not in response["candidates"][0]


def test_http_candidates_do_not_trust_client_current_block(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    candidate = portal.PortalCandidate.from_dict(_payload(settings))
    portal.save_verified_submission(
        settings.portal_db_path,
        candidate,
        VerifyResult(passed=True, reason="ok", build_seconds=0.5),
    )
    monkeypatch.setattr(portal, "get_subtensor", lambda settings: SimpleNamespace(get_current_block=lambda: 11))
    writes: list[tuple[object, dict[str, object]]] = []
    handler = object.__new__(portal._PortalHandler)
    handler.path = "/api/portal/v1/candidates?current_block=999"
    handler.server = SimpleNamespace(settings=settings)
    handler._write_json = lambda status, payload: writes.append((status, payload))

    portal._PortalHandler.do_GET(handler)

    assert writes[0][1]["current_block"] == 11
    assert "proof_script" not in writes[0][1]["candidates"][0]


def test_fetch_portal_candidates_filters_hidden_proofs_and_adds_block(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    hidden = _payload(settings)
    hidden.pop("proof_script")
    revealed = _payload(settings, proof_script="namespace Submission\n-- revealed\n")
    requested: list[tuple[str, float]] = []

    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"candidates": [hidden, revealed]}).encode("utf-8")

    def fake_urlopen(url: str, *, timeout: float) -> Response:
        requested.append((url, timeout))
        return Response()

    monkeypatch.setattr(portal, "urlopen", fake_urlopen)

    candidates = portal.fetch_portal_candidates("https://portal.test/api/portal/v1/candidates?x=1", current_block=50)

    assert requested == [("https://portal.test/api/portal/v1/candidates?x=1&current_block=50", 10.0)]
    assert len(candidates) == 1
    assert candidates[0].proof_script == "namespace Submission\n-- revealed\n"


def test_fetch_portal_candidates_rejects_malformed_response(monkeypatch) -> None:
    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"candidates": {}}'

    monkeypatch.setattr(portal, "urlopen", lambda url, *, timeout: Response())

    with pytest.raises(portal.PortalError, match="candidate list"):
        portal.fetch_portal_candidates("https://portal.test/api/portal/v1/candidates")


def test_portal_state_exposes_submission_stub(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(portal, "get_subtensor", lambda settings: (_ for _ in ()).throw(RuntimeError("offline")))

    state = portal.portal_state(settings)

    assert state["active_target"]["submission_stub"].startswith("import ")
