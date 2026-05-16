# Toolchain and image pinning

Lemma verifies miner proofs with a specific Lean toolchain, Mathlib revision, and sandbox image. These pins affect consensus-facing behavior, so production operators should treat them as release artifacts, not local preferences.

## Sources of truth

| Item | Source |
| ---- | ------ |
| Default Lean toolchain | [`lemma/catalog/constants.py`](../lemma/catalog/constants.py) |
| Default Mathlib revision | [`lemma/catalog/constants.py`](../lemma/catalog/constants.py) |
| Lean template toolchain file | [`lemma/lean/template/lean-toolchain`](../lemma/lean/template/lean-toolchain) |
| Sandbox image build recipe | [`compose/lean.Dockerfile`](../compose/lean.Dockerfile) |
| Runtime sandbox image ref | `LEAN_SANDBOX_IMAGE` |

The local default `lemma/lean-sandbox:latest` is only a developer convenience for images built on the same machine. It is not an immutable production pin.

## Production policy

1. Build the sandbox image from the release checkout.
2. Smoke-test it with the Docker golden test.
3. Publish the image under an immutable tag or digest.
4. Set `LEAN_SANDBOX_IMAGE` to that immutable reference on validators, miners that local-verify, and remote Lean workers.
5. Publish the same `.env` template and validator profile hash for the validator set.

Prefer a digest when your registry workflow supports it:

```text
LEAN_SANDBOX_IMAGE=registry.example/lemma/lean-sandbox@sha256:<digest>
```

An immutable version tag is acceptable only when the operator controls the registry policy and will not retag it.

For high-value operation, publish the resolved digest even if operators use a
human-readable tag in `.env`. A tag is an operator convenience; the digest is
the stronger evidence that everyone can compare.

## Release evidence

Each release should record:

- Git commit and release tag used to build the image;
- full image ref and resolved digest;
- Lean toolchain and Mathlib revision;
- `validator_profile_sha256`, which includes `LEAN_SANDBOX_IMAGE`;
- Docker golden test result;
- generated-template Docker stub/witness gate result when generated supply
  changes.

## Updating pins

When Lean or Mathlib changes, update the constants, template, Dockerfile assumptions, generated/frozen catalog metadata, and operator image ref together. Then rebuild the sandbox image, rerun the golden test, publish the new immutable image ref, and announce the cutover block or release tag.

The validator profile hash (`validator_profile_sha256`) includes the configured sandbox image ref and verification settings. Changing `LEAN_SANDBOX_IMAGE` should therefore change the profile hash operators compare.

Host Lean is for local debugging unless the subnet policy explicitly allows it. If enabled, the host `lake` toolchain must match the published sandbox policy.
