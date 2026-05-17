# Bounties

Bounties are submit-when-ready proof targets. They are separate from timed miner
rounds, and you do not need to be a registered miner to attempt one.

## Flow

```bash
uv run lemma bounty
uv run lemma bounty show
uv run lemma bounty verify starter.two_plus_two --submission Submission.lean
uv run lemma bounty package starter.two_plus_two --submission Submission.lean --payout <SS58>
uv run lemma bounty submit starter.two_plus_two --submission Submission.lean --payout <SS58>
```

`lemma bounty` lists open bounty IDs. `lemma bounty show` opens the only open
bounty directly; when there are several, pass an ID such as
`lemma bounty show starter.two_plus_two`.

`verify` runs the same Lean verification path used by validators, against the
locked target from the bounty registry. `package` verifies, signs with your
Bittensor hotkey, and prints a JSON submission package. `submit` verifies,
signs, then posts to the Lemma bounty API.

The proof is checked as a formal Lean target, not as a claim that an informal
conjecture was solved. Larger bounties may add review or challenge periods for
informal-conjecture significance.

## Proof policy

Lemma bounties are allowlisted. The registry owns the imports, theorem name,
theorem statement, Lean toolchain, Mathlib revision, target hash, and submission
policy.

The default bounty policy is `restricted_helpers`:

- imports must match the registry exactly;
- code must live inside `namespace Submission`;
- helper `def`, `lemma`, and `theorem` declarations are allowed;
- the final theorem must match the exact target theorem and type;
- `sorry`, `admit`, new `axiom` or `constant` declarations, unsafe/native/debug
  hooks, custom syntax/macros/elaborators, notation, attributes, extra imports,
  and target edits are rejected.

The final theorem and helper theorem/lemma declarations are also checked for
axiom dependencies. Only the approved Lean/Mathlib baseline is accepted.

## Registry

The CLI reads a public JSON registry from `LEMMA_BOUNTY_REGISTRY_URL`.
By default this points at the repo-hosted registry path:

```bash
LEMMA_BOUNTY_REGISTRY_URL=https://raw.githubusercontent.com/spacetime-tao/lemma/main/bounties/registry.json
```

Set `LEMMA_BOUNTY_REGISTRY_SHA256_EXPECTED` to pin an exact registry hash. This
is the v1 trust model: HTTPS transport plus an optional SHA256 pin.

Registry schema v1:

```json
{
  "schema_version": 1,
  "bounties": [
    {
      "id": "starter.two_plus_two",
      "kind": "formal_target",
      "title": "Two plus two",
      "status": "open",
      "reward": "No payout",
      "terms_url": "https://lemmasub.net/bounties/",
      "submission_policy": "restricted_helpers",
      "target_sha256": "cfe3cc12caa3ef57ccb6114ca41241c0e6636c4a14d5b30db06745771a67f6f6",
      "source": {
        "name": "Lemma bounty",
        "url": "https://lemmasub.net/bounties/"
      },
      "problem": {
        "id": "starter.two_plus_two",
        "theorem_name": "two_plus_two_eq_four",
        "type_expr": "(2 : Nat) + 2 = 4",
        "split": "starter",
        "lean_toolchain": "leanprover/lean4:v4.30.0-rc2",
        "mathlib_rev": "5450b53e5ddc",
        "imports": ["Mathlib"],
        "extra": {
          "informal_statement": "Prove that two plus two equals four."
        }
      }
    }
  ]
}
```

Formal Conjectures metadata is additive under `source.formal_conjectures`.
Targets marked with an existing `formal_proof` are rejected as normal bounties;
they must be explicitly labeled `kind: "proof_porting"` if Lemma is paying for
porting or simplification rather than a new formal proof.

## Submission API

`lemma bounty submit` posts to:

```text
POST {LEMMA_BOUNTY_API_URL}/v1/bounty-submissions
```

Default:

```bash
LEMMA_BOUNTY_API_URL=https://api.lemmasub.net
LEMMA_BOUNTY_HTTP_TIMEOUT_S=30
```

The submitted JSON contains:

- `schema_version`
- `bounty_id`
- `registry_sha256`
- `proof_script`
- `proof_sha256`
- `submitter_hotkey_ss58`
- `payout_ss58`
- `lemma_version`
- `signature_hex`

The signature is a Sr25519 hotkey signature over a canonical
`LemmaBountySubmissionV1` preimage. It binds the bounty id, registry hash, proof
hash, submitter hotkey, payout address, and Lemma version. The production API
server is intentionally outside this repo; this repo owns the client contract.
