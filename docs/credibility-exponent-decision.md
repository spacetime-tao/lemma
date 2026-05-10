# Credibility exponent decision

## Current policy

Lemma tracks a per-UID verify credibility EMA in the reputation state. Validator Lean
verification moves that value toward `1.0` on pass and `0.0` on fail. The final
reputation-adjusted score is:

```text
ema_score * (credibility ** LEMMA_REPUTATION_CREDIBILITY_EXPONENT)
```

The shipped default is:

```text
LEMMA_REPUTATION_CREDIBILITY_EXPONENT=1.0
```

That means the credibility multiplier is linear. Setting the exponent to `0`
disables the multiplier. Operators can explicitly set `2.5`, but it is not the
live default.

Credibility is a reliability signal, not a proof-quality score. It should fall
when validator Lean verification fails and rise when it passes. It should not try
to detect Lean-valid padding; that belongs to offline proof-metric research in
[proof-intrinsic-decision.md](proof-intrinsic-decision.md).

## Why not default to 2.5 yet?

The knowledge base mentions `credibility^2.5` as an alternative policy. Raising
the live default from `1.0` to `2.5` is a material reward change, not a cleanup
patch. It would make lower credibility much more punitive:

| Credibility | Exponent 1.0 | Exponent 2.5 |
|-------------|--------------|--------------|
| `1.00` | `1.0000` | `1.0000` |
| `0.90` | `0.9000` | `0.7684` |
| `0.75` | `0.7500` | `0.4871` |
| `0.50` | `0.5000` | `0.1768` |

That may be the right policy after calibration, but it should not happen as a
silent default flip. The current default keeps credibility meaningful while
reducing the chance that one validator's local verify state over-penalizes a
miner before the subnet has measured real distributions.

## Change gate

Before changing the default, do all of the following in one intentional release:

- Measure credibility distributions over live or dry-run epochs.
- Decide how sharply failures should compound.
- Update `.env.example`, `LemmaSettings`, profile-hash tests, and operator docs.
- Call out the reward impact in release notes so validators know their
  `judge_profile_sha256` will change.

Do not use an exponent change as a substitute for a better proof-quality metric.
It can make failed verification more expensive, but it cannot distinguish a clean
Lean proof from a padded Lean proof once both pass.
