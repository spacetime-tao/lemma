"""Bounty CLI registry, package, and submission behavior."""

import hashlib
import json
from pathlib import Path

from click.testing import CliRunner
from lemma.cli.main import main

PROBLEM = {
    "id": "fc.test",
    "theorem_name": "test_theorem",
    "type_expr": "True",
    "split": "bounty",
    "lean_toolchain": "leanprover/lean4:v4.15.0",
    "mathlib_rev": "abc123",
    "imports": ["Mathlib"],
    "extra": {"informal_statement": "Prove True."},
}


def _registry(path: Path) -> str:
    raw = json.dumps(
        {
            "schema_version": 1,
            "bounties": [
                {
                    "id": "fc.test",
                    "title": "Test bounty",
                    "status": "open",
                    "reward": "100 TEST",
                    "deadline": "2026-06-01T00:00:00Z",
                    "terms_url": "https://lemmasub.net/bounties/fc.test",
                    "source": {"name": "Formal Conjectures", "url": "https://example.com"},
                    "problem": PROBLEM,
                }
            ],
        },
        sort_keys=True,
    ).encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _proof(path: Path) -> None:
    path.write_text(
        "import Mathlib\n\n"
        "namespace Submission\n\n"
        "theorem test_theorem : True := by trivial\n\n"
        "end Submission\n",
        encoding="utf-8",
    )


def _set_registry_env(monkeypatch, tmp_path: Path) -> str:
    registry_path = tmp_path / "registry.json"
    digest = _registry(registry_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LEMMA_BOUNTY_REGISTRY_URL", str(registry_path))
    monkeypatch.setenv("LEMMA_BOUNTY_REGISTRY_SHA256_EXPECTED", digest)
    return digest


class _VerifyResult:
    passed = True

    def model_dump_json(self, indent: int | None = None) -> str:
        return json.dumps({"passed": True}, indent=indent)


class _FakeHotkey:
    ss58_address = "submitter-hotkey"

    def sign(self, message: bytes) -> bytes:
        assert b"LemmaBountySubmissionV1" in message
        return b"\x01" * 64


class _FakeWallet:
    def __init__(self, name: str, hotkey: str) -> None:
        self.name = name
        self.hotkey_name = hotkey
        self.hotkey = _FakeHotkey()


def test_bounty_list_and_show_use_registry(monkeypatch, tmp_path) -> None:
    digest = _set_registry_env(monkeypatch, tmp_path)

    listed = CliRunner().invoke(main, ["bounty", "list"])
    shown = CliRunner().invoke(main, ["bounty", "show", "fc.test"])

    assert listed.exit_code == 0
    assert "fc.test" in listed.output
    assert digest in listed.output
    assert shown.exit_code == 0
    assert "Test bounty" in shown.output
    assert "lemma bounty verify fc.test" in shown.output


def test_bounty_registry_hash_pin_mismatch_fails(monkeypatch, tmp_path) -> None:
    registry_path = tmp_path / "registry.json"
    _registry(registry_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LEMMA_BOUNTY_REGISTRY_URL", str(registry_path))
    monkeypatch.setenv("LEMMA_BOUNTY_REGISTRY_SHA256_EXPECTED", "0" * 64)

    result = CliRunner().invoke(main, ["bounty", "list"])

    assert result.exit_code != 0
    assert "sha256 mismatch" in result.output


def test_bounty_verify_calls_lean_verify(monkeypatch, tmp_path) -> None:
    _set_registry_env(monkeypatch, tmp_path)
    proof_path = tmp_path / "Submission.lean"
    _proof(proof_path)
    calls: list[tuple[str, str, bool]] = []

    def fake_verify(settings, bounty, proof_script: str, *, host_lean: bool = False):
        calls.append((bounty.id, proof_script, host_lean))
        return _VerifyResult()

    monkeypatch.setattr("lemma.bounty.client.verify_bounty_proof", fake_verify)

    result = CliRunner().invoke(main, ["bounty", "verify", "fc.test", "--submission", str(proof_path)])

    assert result.exit_code == 0
    assert calls == [("fc.test", proof_path.read_text(), False)]
    assert '"passed": true' in result.output


def test_bounty_package_verifies_signs_and_prints_json(monkeypatch, tmp_path) -> None:
    digest = _set_registry_env(monkeypatch, tmp_path)
    proof_path = tmp_path / "Submission.lean"
    _proof(proof_path)
    monkeypatch.setattr("lemma.bounty.client.verify_bounty_proof", lambda *args, **kwargs: _VerifyResult())
    monkeypatch.setattr("bittensor.Wallet", _FakeWallet)

    result = CliRunner().invoke(
        main,
        [
            "bounty",
            "package",
            "fc.test",
            "--submission",
            str(proof_path),
            "--wallet-cold",
            "cold",
            "--wallet-hot",
            "hot",
            "--payout",
            "payout-ss58",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["bounty_id"] == "fc.test"
    assert payload["registry_sha256"] == digest
    assert payload["submitter_hotkey_ss58"] == "submitter-hotkey"
    assert payload["payout_ss58"] == "payout-ss58"
    assert payload["signature_hex"] == "01" * 64


def test_bounty_submit_posts_signed_package(monkeypatch, tmp_path) -> None:
    _set_registry_env(monkeypatch, tmp_path)
    proof_path = tmp_path / "Submission.lean"
    _proof(proof_path)
    submitted: list[dict] = []
    monkeypatch.setattr("lemma.bounty.client.verify_bounty_proof", lambda *args, **kwargs: _VerifyResult())
    monkeypatch.setattr("bittensor.Wallet", _FakeWallet)

    def fake_submit(settings, package: dict) -> dict:
        submitted.append(package)
        return {"status": "accepted", "submission_id": "sub_123"}

    monkeypatch.setattr("lemma.bounty.client.submit_submission_package", fake_submit)

    result = CliRunner().invoke(
        main,
        ["bounty", "submit", "fc.test", "--submission", str(proof_path), "--payout", "payout-ss58"],
    )

    assert result.exit_code == 0
    assert submitted and submitted[0]["bounty_id"] == "fc.test"
    assert json.loads(result.output) == {"status": "accepted", "submission_id": "sub_123"}


def test_bounty_submit_surfaces_api_rejection(monkeypatch, tmp_path) -> None:
    _set_registry_env(monkeypatch, tmp_path)
    proof_path = tmp_path / "Submission.lean"
    _proof(proof_path)
    monkeypatch.setattr("lemma.bounty.client.verify_bounty_proof", lambda *args, **kwargs: _VerifyResult())
    monkeypatch.setattr("bittensor.Wallet", _FakeWallet)

    from lemma.bounty.client import BountyError

    def fake_submit(settings, package: dict) -> dict:
        raise BountyError("bounty API rejected submission (422): failed verification")

    monkeypatch.setattr("lemma.bounty.client.submit_submission_package", fake_submit)

    result = CliRunner().invoke(
        main,
        ["bounty", "submit", "fc.test", "--submission", str(proof_path), "--payout", "payout-ss58"],
    )

    assert result.exit_code != 0
    assert "failed verification" in result.output
