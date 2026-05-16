# Bounties

Bounties are submit-when-ready proof targets. They are separate from timed miner
rounds, and you do not need to be a registered miner to attempt one.

## Flow

```bash
uv run lemma bounty list
uv run lemma bounty show BOUNTY_ID
uv run lemma bounty verify BOUNTY_ID --submission Submission.lean
uv run lemma bounty package BOUNTY_ID --submission Submission.lean --payout <SS58>
uv run lemma bounty submit BOUNTY_ID --submission Submission.lean --payout <SS58>
```

`verify` runs the same Lean verification path used by validators, against the
locked target from the bounty registry. `package` verifies, signs with your
Bittensor hotkey, and prints a JSON submission package. `submit` verifies,
signs, then posts to the Lemma bounty API.

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
      "id": "fc.example",
      "title": "Example bounty",
      "status": "open",
      "reward": "100 TEST",
      "deadline": "2026-06-01T00:00:00Z",
      "terms_url": "https://lemmasub.net/bounties/fc.example",
      "source": {
        "name": "Formal Conjectures",
        "url": "https://google-deepmind.github.io/formal-conjectures/"
      },
      "problem": {
        "id": "fc.example",
        "theorem_name": "example_theorem",
        "type_expr": "True",
        "split": "bounty",
        "lean_toolchain": "leanprover/lean4:v4.15.0",
        "mathlib_rev": "<sha>",
        "imports": ["Mathlib"],
        "extra": {}
      }
    }
  ]
}
```

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
