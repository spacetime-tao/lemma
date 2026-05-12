import json
from pathlib import Path
from types import SimpleNamespace

from tools.public_dashboard import (
    build_theorem_triplet,
    correct_theorem_counts,
    explain_theorem,
    latest_round_proof_count,
    latest_round_proofs,
    public_miner_rows,
    render_public_html,
)


class _Source:
    def sample(self, *, seed: int):
        return SimpleNamespace(
            id=f"gen/{seed}",
            theorem_name=f"lemma_{seed}",
            split="easy",
            type_expr=f"{seed} = {seed}",
        )


def test_build_theorem_triplet_uses_quantize_step() -> None:
    rows = build_theorem_triplet(
        problem_seed=200,
        seed_tag="quantize",
        mode="quantize",
        quantize_blocks=100,
        problem_source=_Source(),
    )

    assert [r.label for r in rows] == ["previous", "current", "next"]
    assert [r.theorem_id for r in rows] == ["gen/100", "gen/200", "gen/300"]
    assert rows[1].plain_english == "Prove that 200 equals 200."
    assert rows[1].explanation == rows[1].plain_english


def test_correct_theorem_counts_deduplicates_within_window(tmp_path: Path) -> None:
    path = tmp_path / "summary.jsonl"
    rows = [
        {"block": 1000, "theorem_id": "a", "uid": 1},
        {"block": 1001, "theorem_id": "a", "uid": 1},
        {"block": 1002, "theorem_id": "b", "uid": 1},
        {"block": 700, "theorem_id": "old", "uid": 2},
        {"block": 1003, "theorem_id": "c", "uid": 2},
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

    counts = correct_theorem_counts(path, current_block=1100, seconds_per_block=12.0, hours=1.0)

    assert counts == {1: 2, 2: 1}


def test_latest_round_proof_count_uses_latest_round_not_24h_total(tmp_path: Path) -> None:
    path = tmp_path / "summary.jsonl"
    rows = [{"block": 1000 + i, "theorem_id": f"old-{i}", "uid": i % 8} for i in range(31)]
    rows += [
        {"block": 2000, "theorem_id": "latest", "uid": 2},
        {"block": 2000, "theorem_id": "latest", "uid": 3},
        {"block": 2000, "theorem_id": "latest", "uid": 4},
        {"block": 2000, "theorem_id": "latest", "uid": 5},
        {"block": 2000, "theorem_id": "latest", "uid": 6},
        {"block": 2000, "theorem_id": "latest", "uid": 7},
        {"block": 2000, "theorem_id": "latest", "uid": 7},
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

    counts = correct_theorem_counts(path, current_block=2100, seconds_per_block=12.0, hours=24.0)

    assert sum(counts.values()) == 37
    assert latest_round_proof_count(path) == 6
    assert latest_round_proofs(path).passed_uids == frozenset({2, 3, 4, 5, 6, 7})


def test_public_miner_rows_are_sorted_by_score() -> None:
    metagraph = SimpleNamespace(
        n=2,
        hotkeys=["hot-0", "hot-1"],
        coldkeys=["cold-0", "cold-1"],
        I=[0.1, 0.9],
    )

    rows = public_miner_rows(
        metagraph,
        {1: 3},
        passed_prior_round_uids=frozenset({1}),
        network="finney",
        netuid=1,
        uid_url_template="https://example.invalid/subnet/{netuid}/uid/{uid}",
        account_url_template="https://example.invalid/account/{address}",
    )

    assert [r.uid for r in rows] == [1, 0]
    assert rows[0].hotkey == "hot-1"
    assert rows[0].coldkey == "cold-1"
    assert rows[0].score == 0.9
    assert rows[0].correct_theorems_24h == 3
    assert rows[0].passed_prior_round is True
    assert rows[1].passed_prior_round is False
    assert rows[0].uid_url == "https://example.invalid/subnet/1/uid/1"
    assert rows[0].hotkey_url == "https://example.invalid/account/hot-1"


def test_explain_theorem_and_render_sortable_table() -> None:
    explanation = explain_theorem(
        type_expr="forall n : Nat, n * 1 = n",
        split="easy",
        topic="algebra.nat",
    )
    assert "natural number" in explanation
    assert "times" in explanation
    assert "easy" not in explanation
    assert "statement" not in explanation

    html = render_public_html(
        {
            "generated_at": "2026-05-11T00:00:00Z",
            "problem_seed_mode": "quantize",
            "problem_seed_quantize_blocks": 100,
            "block_time_sec_estimate": 12.0,
            "score_source": "metagraph_incentive",
            "theorems": {
                "current": {
                    "theorem_id": "gen/1",
                    "name": "t_1",
                    "split": "easy",
                    "type_expr": "True",
                    "plain_english": "Prove that True.",
                    "explanation": "A true statement.",
                },
            },
            "miners": [
                {
                    "uid": 1,
                    "coldkey": "cold",
                    "hotkey": "hot",
                    "score": 0.5,
                    "passed_prior_round": True,
                    "correct_theorems_24h": 2,
                    "uid_url": "https://example.invalid/uid/1",
                },
            ],
        },
    )
    assert "Problem Rubric" in html
    assert 'data-sort="number"' in html
    assert "Passed Previous Round" in html
    assert "Prove that True." in html
    assert 'href="https://example.invalid/uid/1"' in html
