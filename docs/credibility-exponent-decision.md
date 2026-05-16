# Credibility exponent decision

## Historical policy

Lemma previously tracked a per-UID verify credibility EMA in the reputation
state and used this final reputation-adjusted score:

```text
ema_score * (credibility ** LEMMA_REPUTATION_CREDIBILITY_EXPONENT)
```

The shipped default is:

```text
LEMMA_REPUTATION_CREDIBILITY_EXPONENT=1.0
```

The live weight path now uses difficulty-weighted `rolling_score_by_uid`.
`ema_by_uid` and `credibility_by_uid` remain loadable in
`LEMMA_REPUTATION_STATE_PATH` for compatibility, but the credibility exponent is
not part of the default chain-weight formula.

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

That may be a future policy after calibration, but it should not happen as a
silent default flip. Reintroducing it would make one validator's local verify
state directly affect live miner weights again.

## Change gate

Before reintroducing a credibility exponent into live weights, do all of the
following in one intentional release:

- Measure credibility distributions over live or dry-run epochs.
- Decide how sharply failures should compound.
- Update `.env.example`, `LemmaSettings`, profile-hash tests, and operator docs.
- Call out the reward impact in release notes so validators know their
  `judge_profile_sha256` will change.

Do not use an exponent change as a substitute for a better proof-quality metric.
It can make failed verification more expensive, but it cannot distinguish a clean
Lean proof from a padded Lean proof once both pass.
