from tools.ops_dashboard import (
    _parse_latest_epoch,
    _parse_latest_set_weights,
    _parse_listeners,
    _parse_miner_summaries,
    _parse_services,
)


def test_parse_services() -> None:
    rows = _parse_services(
        """
  UNIT                 LOAD   ACTIVE SUB     DESCRIPTION
  lemma-miner.service  loaded active running Lemma miner
  lemma-validator.service loaded failed failed Lemma validator
"""
    )

    assert [(row.name, row.active, row.sub) for row in rows] == [
        ("lemma-miner.service", "active", "running"),
        ("lemma-validator.service", "failed", "failed"),
    ]


def test_parse_latest_epoch_and_set_weights() -> None:
    logs = "\n".join(
        [
            "2026-05-11 04:03:07 | INFO | lemma_epoch_summary "
            "chain_head_block=7095707 split=easy theorem_id=gen/7095700 "
            "verified=5 scored=5 pareto_entries=5 skip_set_weights=False "
            "seconds=377.34  [verified=Lean proof OK]",
            "2026-05-11 04:03:11 | INFO | set_weights success=True "
            "message=Not waiting for finalization or inclusion.",
        ]
    )

    assert _parse_latest_epoch(logs)["scored"] == "5"
    assert _parse_latest_epoch(logs)["theorem_id"] == "gen/7095700"
    assert _parse_latest_set_weights(logs)["success"] == "True"


def test_parse_miner_logs() -> None:
    logs = "\n".join(
        [
            "2026-05-11 20:55:03 | INFO | Miner axon listening "
            "netuid=467 port=8091 hotkey=5abc",
            "2026-05-11 20:55:04 | INFO | miner_forward_summary "
            "theorem_id=gen/1 split=easy prover_s=1.25s proof_chars=88 "
            "session_forwards=2 session_avg_prover_s=1.50s "
            "session_local_ok=1 session_local_fail=0",
        ]
    )

    assert _parse_listeners(logs) == [{"netuid": "467", "port": "8091", "hotkey": "5abc"}]
    assert _parse_miner_summaries(logs)[0]["prover_s"] == "1.25"
