# Problem catalog sources

Validators sample challenges from ``lemma/problems/minif2f_frozen.json`` (any merged Lean 4 catalog in that schema). Build or refresh it with:

```bash
# merged catalog (recommended)
uv sync --extra catalog    # only needed for FormalMATH (--sources formalmath_lite / formalmath_all)
python scripts/build_lemma_catalog.py \
  --out lemma/problems/minif2f_frozen.json \
  --sources yangky,dm,putnam

# single-repo shortcut (yangky11 miniF2F-lean4 only)
python scripts/load_minif2f.py --out lemma/problems/minif2f_frozen.json
```

## Upstream repositories

| Phase | Dataset | Repository | Notes |
| ----- | ------- | ---------- | ----- |
| 1 | miniF2F (Lean 4 community) | [yangky11/miniF2F-lean4](https://github.com/yangky11/miniF2F-lean4) | Source key: ``yangky`` |
| 1 | miniF2F (DeepMind fork) | [google-deepmind/miniF2F](https://github.com/google-deepmind/miniF2F) | Source key: ``dm`` |
| 1 | miniF2F (original, polyglot) | [openai/miniF2F](https://github.com/openai/miniF2F) | **Lean 3** under ``lean/`` — not ingested; use Lean 4 forks above |
| 2 | Putnam (Lean 4) | [trishullab/PutnamBench](https://github.com/trishullab/PutnamBench) ``lean4/src`` | Source key: ``putnam`` |
| 2 | FormalMATH | Hugging Face [SphereLab/FormalMATH-Lite](https://huggingface.co/datasets/SphereLab/FormalMATH-Lite) / [FormalMATH-All](https://huggingface.co/datasets/SphereLab/FormalMATH-All) | Keys: ``formalmath_lite``, ``formalmath_all`` (requires ``uv sync --extra catalog``) |
| 3 | mathlib4 sample | [leanprover-community/mathlib4](https://github.com/leanprover-community/mathlib4) | Source key: ``mathlib`` — pass ``--mathlib-root`` to a local clone; samples ``theorem … : … := by sorry`` lines |

FormalMATH rows use ``autoformalization`` text from the HF dataset (imports + theorem stub).

### Bring-your-own rows

- ``--merge-json PATH``: append JSON arrays in the same schema as ``minif2f_frozen.json`` (required scalar keys per row). Repeat the flag for multiple files.
- ``--extra-repo URL REF PREFIX``: clone **any** public Lean repo. If it contains ``MiniF2F/Test`` (and optionally ``Valid``), the builder uses the miniF2F parser; otherwise it **loose-scans** ``*.lean`` (skipping ``.lake``) for ``theorem … := by sorry`` stubs, up to ``--extra-repo-max-files``.

Examples:

```bash
python scripts/build_lemma_catalog.py --sources yangky,dm \
  --merge-json ./my_fragment.json \
  --extra-repo https://github.com/org/some-lean-benchmark.git main bench1
```

### Not ingested automatically (why)

| Artifact | Reason |
| -------- | ------ |
| [openai/miniF2F](https://github.com/openai/miniF2F) ``lean/`` | Lean **3** |
| [SorryDB](https://github.com/SorryDB/SorryDB) snapshots | Index is repo **coordinates + goals**, not a standalone Challenge/Solution slice; use their tooling or export into Lemma JSON yourself |
| [InternLM/Lean-GitHub](https://huggingface.co/datasets/InternLM/Lean-GitHub) (HF) | **Tactic** traces / states, not ``sorry`` theorem stubs |
| [FormalQualBench](https://github.com/math-inc/FormalQualBench) | Namespaced ``MainTheorem`` modules; needs a dedicated bridge (future) |

## ID prefixes

Merged IDs are prefixed by source (``yk/``, ``dm/``, ``putnam/``, ``formalmath/``, ``mathlib/``) to avoid collisions.

## Topic tags

``scripts/build_lemma_catalog.py`` sets a default string field ``topic`` per source (e.g. ``miniF2F/yangky``, ``putnam``, ``formalmath/lite``, ``mathlib/sample``, ``extra/<prefix>``, ``catalog/merge``). Custom fragments merged via ``--merge-json`` keep any explicit ``topic`` already in the file (``setdefault``). Downstream code reads tags via [`Problem.extra`](../lemma/problems/base.py) when present on catalog rows.

## Toolchain alignment

Pins in each JSON row must match the sandbox Docker image (see ``compose/lean.Dockerfile``). PutnamBench rows pick ``lean-toolchain`` from its own repo when present.
