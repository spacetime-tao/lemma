# Catalog Sources

Lemma has two problem sources:

- `generated`: default live-style source.
- `frozen`: public eval catalog for dev use.

## Generated Source

`LEMMA_PROBLEM_SOURCE=generated` turns a chain-aligned seed into one theorem id,
such as `gen/<seed>`.

Validators agree when they share:

- chain head;
- seed mode;
- generated registry hash;
- release version.

Template selection mixes the seed with SHA256 before using `random.Random`. This
reduces adjacent-seed correlation. It does not hide the map from seed to problem.
Anyone can still precompute public generated problems.

Rollback only:

```bash
LEMMA_GENERATED_LEGACY_PLAIN_RNG=1
```

## RPC Head Slack

`LEMMA_PROBLEM_SEED_CHAIN_HEAD_SLACK_BLOCKS` subtracts blocks from the RPC head
before seed and deadline math.

Default is `0`. Setting `1` can reduce one-block disagreements at quantize
boundaries.

## Frozen Catalog

Use `generated` for production-style runs.

The frozen catalog is a public eval set. To enable it, set:

```bash
LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1
LEMMA_PROBLEM_SOURCE=frozen
```

Without the dev flag, frozen mode fails closed.

Build frozen JSON with:

```bash
uv sync --extra catalog
python scripts/build_lemma_catalog.py \
  --out lemma/problems/minif2f_frozen.json \
  --sources yangky,dm,putnam
```

## Sources

| Key | Upstream |
| --- | --- |
| `yangky` | [yangky11/miniF2F-lean4](https://github.com/yangky11/miniF2F-lean4) |
| `dm` | [google-deepmind/miniF2F](https://github.com/google-deepmind/miniF2F) |
| `putnam` | [PutnamBench](https://github.com/trishullab/PutnamBench) `lean4/src` |
| `formalmath_*` | HF [FormalMATH-Lite](https://huggingface.co/datasets/SphereLab/FormalMATH-Lite) / [FormalMATH-All](https://huggingface.co/datasets/SphereLab/FormalMATH-All) |
| `mathlib` | Local mathlib clone via `--mathlib-root` |

The [openai/miniF2F](https://github.com/openai/miniF2F) `lean/` folder is Lean
3. Use Lean 4 sources for Lemma.

## Extra Inputs

- `--merge-json`: append compatible JSON fragments.
- `--extra-repo URL REF PREFIX`: clone public repos and scan for theorem stubs.

## Not Ingested

| Source | Reason |
| --- | --- |
| SorryDB | Different schema. |
| Lean-GitHub (HF) | Tactic traces, not theorem stubs. |
| FormalQualBench | Needs a dedicated bridge. |

## Metadata

Merged ids use prefixes such as `yk/` and `dm/`.

`lean_toolchain` and `mathlib_rev` must match
[`compose/lean.Dockerfile`](../compose/lean.Dockerfile).
