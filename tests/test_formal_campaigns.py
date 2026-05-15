import json

import pytest
from lemma.formal_campaigns import (
    CAMPAIGN_REWARD_MODE,
    FormalCampaign,
    append_campaign_acceptance,
    load_campaigns,
    new_campaign_acceptance,
    proof_declares_campaign_theorem,
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


def test_acceptance_ledger_is_append_only(tmp_path) -> None:
    path = tmp_path / "campaign-ledger.jsonl"
    acceptance = new_campaign_acceptance(
        campaign_id="fc.agoh_giuga",
        solver_uid=7,
        solver_hotkey="hotkey-7",
        proof_sha256="b" * 64,
    )

    append_campaign_acceptance(path, acceptance)

    row = json.loads(path.read_text(encoding="utf-8"))
    assert row["campaign_id"] == "fc.agoh_giuga"
    assert row["reward_mode"] == CAMPAIGN_REWARD_MODE
    with pytest.raises(ValueError, match="already accepted"):
        append_campaign_acceptance(path, acceptance)
