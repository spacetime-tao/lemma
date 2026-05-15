import json

import pytest
from lemma.formal_campaigns import (
    CAMPAIGN_REWARD_MODE,
    FormalCampaign,
    append_campaign_acceptance,
    bounty_signature_message,
    build_bounty_package,
    load_campaign_acceptances,
    load_campaigns,
    new_campaign_acceptance,
    proof_declares_campaign_theorem,
    public_campaigns_payload,
    validate_campaign_registry,
)


def _campaign(**updates: object) -> dict[str, object]:
    data: dict[str, object] = {
        "id": "fc.agoh_giuga",
        "title": "Agoh Giuga",
        "status": "open",
        "source_url": "https://google-deepmind.github.io/formal-conjectures/",
        "upstream_repo": "google-deepmind/formal-conjectures",
        "upstream_commit": "abc123",
        "lean_file": "FormalConjectures/Wikipedia/AgohGiuga.lean",
        "declaration": "AgohGiuga.isWeakGiuga_iff_prime_dvd",
        "statement_sha256": "a" * 64,
        "reward_label": "1k SN467 alpha",
        "type_expr": "True",
        "challenge_full": "import Mathlib\n\ntheorem isWeakGiuga_iff_prime_dvd : True := by\n  sorry\n",
        "submission_stub": (
            "import Mathlib\n\nnamespace Submission\n\n"
            "theorem isWeakGiuga_iff_prime_dvd : True := by\n  sorry\n\nend Submission\n"
        ),
        "lean_toolchain": "leanprover/lean4:v4.30.0-rc2",
        "mathlib_rev": "5450b53e5ddc",
        "bounty_note": "Owner-emission WTA campaign.",
    }
    data.update(updates)
    return data


def test_default_formal_campaign_registry_loads() -> None:
    assert load_campaigns() == []


def test_campaign_registry_rejects_duplicate_ids() -> None:
    data = {"schema": "lemma_formal_conjectures_campaigns_v1", "campaigns": [_campaign(), _campaign()]}

    with pytest.raises(ValueError, match="duplicate campaign id"):
        validate_campaign_registry(data)


def test_campaign_exact_declaration_preflight() -> None:
    campaign = FormalCampaign.from_dict(_campaign())

    assert proof_declares_campaign_theorem(
        campaign,
        "namespace AgohGiuga\n\ntheorem isWeakGiuga_iff_prime_dvd : True := by\n  trivial\n",
    )
    assert not proof_declares_campaign_theorem(campaign, "theorem other_name : True := by\n  trivial\n")


def test_campaign_to_problem_uses_pinned_statement() -> None:
    campaign = FormalCampaign.from_dict(_campaign())
    problem = campaign.to_problem()

    assert problem.id == "bounty/fc.agoh_giuga"
    assert problem.type_expr == "True"
    assert problem.extra["source_url"] == "https://google-deepmind.github.io/formal-conjectures/"
    assert problem.challenge_source().startswith("import Mathlib")


def test_bounty_package_signing_message_is_provider_neutral() -> None:
    campaign = FormalCampaign.from_dict(_campaign())
    proof = "theorem isWeakGiuga_iff_prime_dvd : True := by\n  trivial\n"
    package = build_bounty_package(
        campaign=campaign,
        proof_script=proof,
        solver_hotkey="hotkey",
        signature_hex="sig",
        verify_reason="ok",
        build_seconds=1.0,
        created_unix=123,
    )

    assert package["campaign"]["reward_label"] == "1k SN467 alpha"
    assert package["solver"]["signature_message"] == bounty_signature_message(
        campaign,
        package["proof"]["proof_sha256"],
    ).decode("utf-8")
    assert package["proof"]["proof_script"].endswith("\n")


def test_public_campaign_payload_hides_submission_details() -> None:
    campaign = FormalCampaign.from_dict(_campaign())
    acceptance = new_campaign_acceptance(
        campaign_id="fc.agoh_giuga",
        solver_hotkey="hotkey-7",
        proof_sha256="b" * 64,
    )
    payload = public_campaigns_payload([campaign], acceptances=[acceptance], generated_unix=123)
    text = json.dumps(payload, sort_keys=True)

    assert payload["schema_version"] == 1
    assert payload["campaigns"][0]["reward_label"] == "1k SN467 alpha"
    assert payload["campaigns"][0]["status"] == "accepted"
    assert payload["campaigns"][0]["accepted"]["solver_hotkey"] == "hotkey-7"
    assert payload["campaigns"][0]["accepted"]["reward_status"] == "accepted"
    assert "solver_uid" not in payload["campaigns"][0]["accepted"]
    assert "submission_stub" not in text
    assert "challenge_full" not in text
    assert "proof_sha256" not in text


def test_acceptance_ledger_is_append_only(tmp_path) -> None:
    path = tmp_path / "campaign-ledger.jsonl"
    acceptance = new_campaign_acceptance(
        campaign_id="fc.agoh_giuga",
        solver_hotkey="hotkey-7",
        proof_sha256="b" * 64,
    )

    append_campaign_acceptance(path, acceptance)

    row = json.loads(path.read_text(encoding="utf-8"))
    assert row["campaign_id"] == "fc.agoh_giuga"
    assert row["solver_hotkey"] == "hotkey-7"
    assert row["solver_uid"] is None
    assert row["reward_mode"] == CAMPAIGN_REWARD_MODE
    assert load_campaign_acceptances(path)[0].solver_hotkey == "hotkey-7"
    with pytest.raises(ValueError, match="already accepted"):
        append_campaign_acceptance(path, acceptance)
