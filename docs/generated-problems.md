# Generated Problems

`LEMMA_PROBLEM_SOURCE=generated` is the default.

Each round maps chain state to a `problem_seed`. The seed picks one theorem from
[`generated.py`](../lemma/problems/generated.py).

Default seed mode:

```text
LEMMA_PROBLEM_SEED_MODE=quantize
LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS=100
```

`subnet_epoch` can use Bittensor Tempo instead.

Same code plus same seed gives the same `Problem`.

## How Many Problems?

There are 40 template builders today:

- 10 easy;
- 22 medium;
- 8 hard.

A builder is a recipe. It can produce many instances by changing numbers or
details from the seed.

So there are not only 40 total problems. There are 40 families that can produce
many statements.

Topics are labels for logs and exports. They are not separate proof rules.

## Honest Limit

Generated problems are variations inside fixed templates. They are not every
possible theorem in math.

Miners may learn repeating shapes over time. More diversity comes from adding
builders, frozen/catalog problems, or future bounty lanes. See
[problem-supply-policy.md](problem-supply-policy.md).

## Template Mix

Current rough mix:

- 25% easy;
- 55% medium;
- 20% hard.

Easy templates fit quick tactics. Medium templates look like common Mathlib
exercises. Hard templates target longer proofs.

## Timeouts

The generator does not set time limits.

Subnet policy sets:

- miner forward wait;
- `LEAN_VERIFY_TIMEOUT_S`;
- validator cadence.

See [governance.md](governance.md).

## Scoring

Each epoch is independent:

1. Miner returns proof.
2. Lean checks proof.
3. Passing proof enters scoring.
4. Validator writes weights for that round.

| Outcome | Result |
| --- | --- |
| Timeout | No proof score. |
| Lean fails | No proof score. |
| Lean passes | Enters scoring. |

Related docs:

- [faq.md](faq.md)
- [catalog-sources.md](catalog-sources.md)
- [problem-supply-policy.md](problem-supply-policy.md)
