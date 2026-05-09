# Catalog sources

## Generated templates (default)

**`LEMMA_PROBLEM_SOURCE=generated`** expands a **chain-aligned integer seed** into one theorem per round (`gen/<seed>` ids). Validators agree because they share head + seed mode + registry pin.

Template selection uses a **deterministic SHA256 mix** of that seed before `random.Random` (see [`generated.py`](../lemma/problems/generated.py)). That decorrelates **adjacent** chain seeds (same window still shares one `problem_seed` in quantize mode). It does **not** remove the public, deterministic map from seed → problem: anyone can still precompute. This is documented as an accepted supply boundary in [problem-supply-policy.md](problem-supply-policy.md). To match an **older** Lemma release’s expansion exactly, set **`LEMMA_GENERATED_LEGACY_PLAIN_RNG=1`** (rollback only).

**RPC head slack:** Optional **`LEMMA_PROBLEM_SEED_CHAIN_HEAD_SLACK_BLOCKS`** (default **0**) subtracts that many blocks from the RPC head **before** `resolve_problem_seed` and forward HTTP deadline math (validators, `lemma status`, `lemma-cli try-prover`, `lemma problems show`). Setting **`1`** often removes **one-block** disagreements on `get_current_block()` at quantize boundaries (e.g. head **199** vs **200** with `quantize_blocks=100` can disagree without slack; both map to the same seed with slack **1**).

## Frozen catalog (`frozen` mode)

**Production-style deployments:** use **`LEMMA_PROBLEM_SOURCE=generated`**. The frozen catalog is a **public eval set** — enable only on purpose.

To use frozen JSON, set **`LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1`** in `.env` together with **`LEMMA_PROBLEM_SOURCE=frozen`**. Without this flag, `get_problem_source`, direct frozen-id `resolve_problem` calls, and `lemma validator-check` reject frozen mode.

Validators with `LEMMA_PROBLEM_SOURCE=frozen` read `lemma/problems/minif2f_frozen.json`. Rebuild with:

```bash
uv sync --extra catalog   # FormalMATH sources only
python scripts/build_lemma_catalog.py \
  --out lemma/problems/minif2f_frozen.json \
  --sources yangky,dm,putnam
```

## Sources

| Key | Upstream |
| --- | -------- |
| `yangky` | [yangky11/miniF2F-lean4](https://github.com/yangky11/miniF2F-lean4) |
| `dm` | [google-deepmind/miniF2F](https://github.com/google-deepmind/miniF2F) |
| `putnam` | [PutnamBench](https://github.com/trishullab/PutnamBench) `lean4/src` |
| `formalmath_*` | HF [FormalMATH-Lite](https://huggingface.co/datasets/SphereLab/FormalMATH-Lite) / [FormalMATH-All](https://huggingface.co/datasets/SphereLab/FormalMATH-All) |
| `mathlib` | Local mathlib clone via `--mathlib-root` |

[openai/miniF2F](https://github.com/openai/miniF2F) `lean/` is Lean 3 — use Lean 4 forks above.

## Extra inputs

- `--merge-json`: append compatible JSON fragments (repeat allowed).
- `--extra-repo URL REF PREFIX`: clone public repos; miniF2F layout or loose scan for `theorem … := by sorry`.

## Not ingested

| Source | Reason |
| ------ | ------ |
| SorryDB | Different schema |
| Lean-GitHub (HF) | Tactic traces, not stubs |
| FormalQualBench | Needs dedicated bridge |

## IDs and metadata

Merged IDs use prefixes (`yk/`, `dm/`, …). Builder sets `topic` where absent ([`Problem.extra`](../lemma/problems/base.py)).

## Toolchain

Row `lean_toolchain` / `mathlib_rev` must match [`compose/lean.Dockerfile`](../compose/lean.Dockerfile).
