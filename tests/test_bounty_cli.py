"""Bounty/escrow CLI registry and transaction-package behavior."""

import hashlib
import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from lemma.bounty.client import BountyError, load_registry, target_sha256
from lemma.cli.main import main
from lemma.lean.problem_codec import problem_from_payload

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
            "schema_version": 2,
            "reward_custody": "evm_escrow",
            "bounties": [
                {
                    "id": "fc.test",
                    "title": "Test bounty",
                    "status": "active",
                    "reward": "1 TAO escrowed",
                    "deadline": "2026-06-01T00:00:00Z",
                    "terms_url": "https://lemmasub.net/#escrow",
                    "source": {"name": "Formal Conjectures", "url": "https://example.com"},
                    "policy_version": "bounty-policy-v1",
                    "toolchain_id": "leanprover/lean4:v4.15.0",
                    "escrow": {
                        "chain_id": 945,
                        "contract_address": "0x" + "aa" * 20,
                        "bounty_id": 7,
                        "funded": True,
                        "funding_confirmed_block": 12345,
                    },
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
    public_key = b"\x77" * 32

    def sign(self, message: bytes) -> bytes:
        assert b"LemmaBounty" in message
        return b"\x01" * 64


class _FakeWallet:
    def __init__(self, name: str, hotkey: str) -> None:
        self.name = name
        self.hotkey_name = hotkey
        self.hotkey = _FakeHotkey()


def test_help_exposes_only_public_commands() -> None:
    result = CliRunner().invoke(main, ["--help"])

    assert result.exit_code == 0
    assert set(main.commands) == {"setup", "mine", "status", "validate"}
    for command in ("setup", "mine", "status", "validate"):
        assert command in result.output


def test_mine_list_and_show_use_registry(monkeypatch, tmp_path) -> None:
    digest = _set_registry_env(monkeypatch, tmp_path)

    default = CliRunner().invoke(main, ["mine"])
    shown = CliRunner().invoke(main, ["mine", "fc.test"])
    status = CliRunner().invoke(main, ["status"])
    check = CliRunner().invoke(main, ["validate", "--check"])

    assert default.exit_code == 0
    assert "Escrow-backed" in default.output
    assert "fc.test" in default.output
    assert digest in default.output
    assert shown.exit_code == 0
    assert "Test bounty" in shown.output
    assert "target_sha256" in shown.output
    assert "policy" in shown.output
    assert "lemma mine fc.test --submission Submission.lean" in shown.output
    assert status.exit_code == 0
    assert "Lemma escrow status" in status.output
    assert check.exit_code == 0
    assert "READY" in check.output


def test_bounty_registry_hash_pin_mismatch_fails(monkeypatch, tmp_path) -> None:
    registry_path = tmp_path / "registry.json"
    _registry(registry_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LEMMA_BOUNTY_REGISTRY_URL", str(registry_path))
    monkeypatch.setenv("LEMMA_BOUNTY_REGISTRY_SHA256_EXPECTED", "0" * 64)

    result = CliRunner().invoke(main, ["mine"])

    assert result.exit_code != 0
    assert "sha256 mismatch" in result.output


def test_bounty_registry_rejects_target_hash_mismatch() -> None:
    payload = {
        "schema_version": 1,
        "bounties": [
            {
                "id": "fc.test",
                "title": "Test bounty",
                "status": "open",
                "reward": "100 TEST",
                "source": {"name": "Formal Conjectures"},
                "target_sha256": "0" * 64,
                "problem": PROBLEM,
            }
        ],
    }

    with pytest.raises(BountyError, match="target_sha256 mismatch"):
        load_registry(json.dumps(payload).encode())


def test_bounty_registry_rejects_formal_proof_normal_bounty() -> None:
    payload = {
        "schema_version": 1,
        "bounties": [
            {
                "id": "fc.test",
                "title": "Test bounty",
                "status": "open",
                "reward": "100 TEST",
                "source": {
                    "name": "Formal Conjectures",
                    "formal_conjectures": {"formal_proof": True, "formal_proof_url": "https://example.com/proof.lean"},
                },
                "problem": PROBLEM,
            }
        ],
    }

    with pytest.raises(BountyError, match="formal_proof"):
        load_registry(json.dumps(payload).encode())


def test_bounty_registry_allows_formal_proof_porting_bounty() -> None:
    problem = problem_from_payload(PROBLEM)
    payload = {
        "schema_version": 1,
        "bounties": [
            {
                "id": "fc.test",
                "kind": "proof_porting",
                "title": "Test bounty",
                "status": "open",
                "reward": "100 TEST",
                "source": {
                    "name": "Formal Conjectures",
                    "formal_conjectures": {"formal_proof_url": "https://example.com/proof.lean"},
                },
                "target_sha256": target_sha256(problem),
                "problem": PROBLEM,
            }
        ],
    }

    registry = load_registry(json.dumps(payload).encode())

    assert registry.get("fc.test").kind == "proof_porting"
    assert registry.get("fc.test").submission_policy == "restricted_helpers"


def test_mine_submission_calls_lean_verify(monkeypatch, tmp_path) -> None:
    _set_registry_env(monkeypatch, tmp_path)
    proof_path = tmp_path / "Submission.lean"
    _proof(proof_path)
    calls: list[tuple[str, str, bool]] = []

    def fake_verify(settings, bounty, proof_script: str, *, host_lean: bool = False):
        calls.append((bounty.id, proof_script, host_lean))
        return _VerifyResult()

    monkeypatch.setattr("lemma.bounty.client.verify_bounty_proof", fake_verify)

    result = CliRunner().invoke(main, ["mine", "fc.test", "--submission", str(proof_path)])

    assert result.exit_code == 0
    assert calls == [("fc.test", proof_path.read_text(), False)]
    assert '"passed": true' in result.output
    assert "Add --commit or --reveal" in result.output


def test_public_mine_builds_escrow_commit_package(monkeypatch, tmp_path) -> None:
    raw = json.dumps(
        {
            "schema_version": 2,
            "reward_custody": "evm_escrow",
            "bounties": [
                {
                    "id": "fc.test",
                    "title": "Test bounty",
                    "status": "active",
                    "reward": "1 TAO escrowed",
                    "source": {"name": "Formal Conjectures"},
                    "policy_version": "bounty-policy-v1",
                    "toolchain_id": "leanprover/lean4:v4.15.0",
                    "escrow": {
                        "chain_id": 945,
                        "contract_address": "0x" + "aa" * 20,
                        "bounty_id": 7,
                        "funded": True,
                        "funding_confirmed_block": 12345,
                    },
                    "problem": PROBLEM,
                }
            ],
        },
        sort_keys=True,
    ).encode()
    registry_path = tmp_path / "registry.json"
    registry_path.write_bytes(raw)
    proof_path = tmp_path / "Submission.lean"
    output_path = tmp_path / "claim.json"
    _proof(proof_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LEMMA_BOUNTY_REGISTRY_URL", str(registry_path))
    monkeypatch.setenv("LEMMA_BOUNTY_REGISTRY_SHA256_EXPECTED", hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr("lemma.bounty.client.verify_bounty_proof", lambda *args, **kwargs: _VerifyResult())
    monkeypatch.setattr("bittensor.Wallet", _FakeWallet)

    result = CliRunner().invoke(
        main,
        [
            "mine",
            "fc.test",
            "--submission",
            str(proof_path),
            "--commit",
            "--claimant-evm",
            "0x" + "88" * 20,
            "--payout-evm",
            "0x" + "99" * 20,
            "--salt",
            "0x" + "33" * 32,
            "--wallet-cold",
            "cold",
            "--wallet-hot",
            "hot",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(output_path.read_text())
    assert payload["type"] == "lemma_bounty_commitment_v1"
    assert payload["escrow_bounty_id"] == 7
    assert payload["transaction"]["to"] == "0x" + "aa" * 20
    assert payload["transaction"]["data"].startswith("0xede854e6")
    assert payload["submitter_hotkey_pubkey"] == "0x" + "77" * 32
    assert payload["identity_binding_signature_hex"] == "01" * 64


def test_setup_writes_bounty_only_env(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    env_path = tmp_path / ".env"

    result = CliRunner().invoke(
        main,
        [
            "setup",
            "--env-file",
            str(env_path),
            "--registry-url",
            "registry.json",
            "--registry-sha256",
            "a" * 64,
            "--escrow-contract",
            "0x" + "aa" * 20,
            "--evm-rpc-url",
            "https://rpc.example",
            "--evm-chain-id",
            "945",
            "--wallet-cold",
            "cold",
            "--wallet-hot",
            "hot",
        ],
    )

    assert result.exit_code == 0
    text = env_path.read_text()
    assert 'LEMMA_BOUNTY_REWARD_CUSTODY="evm_escrow"' in text
    assert 'LEMMA_BOUNTY_REGISTRY_URL="registry.json"' in text
    assert 'LEMMA_BOUNTY_REGISTRY_SHA256_EXPECTED="' + ("a" * 64) + '"' in text
    assert 'BT_WALLET_COLD="cold"' in text
    assert 'BT_WALLET_HOT="hot"' in text
