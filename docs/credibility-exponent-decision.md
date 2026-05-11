# Credibility Exponent Decision

## Current Policy

Lemma tracks per-UID verify credibility in the reputation state.

Validator Lean verification moves credibility:

- toward `1.0` when Lean passes;
- toward `0.0` when Lean fails.

The final reputation-adjusted score uses:

```text
ema_score * (credibility ** LEMMA_REPUTATION_CREDIBILITY_EXPONENT)
```

The default is:

```text
LEMMA_REPUTATION_CREDIBILITY_EXPONENT=1.0
```

That is a linear multiplier. Setting the exponent to `0` disables it.

Credibility is a reliability signal. It is not a proof-quality score. It should
not try to detect Lean-valid padding. Study that offline in
[proof-intrinsic-decision.md](proof-intrinsic-decision.md).

## Why Not Default To 2.5?

The knowledge base mentions `credibility^2.5` as an option. Making it the live
default would be a reward change, not cleanup.

| Credibility | Exponent 1.0 | Exponent 2.5 |
| --- | --- | --- |
| `1.00` | `1.0000` | `1.0000` |
| `0.90` | `0.9000` | `0.7684` |
| `0.75` | `0.7500` | `0.4871` |
| `0.50` | `0.5000` | `0.1768` |

That may be useful after measurement. It should not be a silent default flip.

## Change Gate

Before changing the default:

1. Measure credibility over live or dry-run epochs.
2. Decide how sharply failures should compound.
3. Update `.env.example`, `LemmaSettings`, profile-hash tests, and docs.
4. Call out the reward impact in release notes.

Do not use exponent changes as a substitute for proof-quality metrics.
