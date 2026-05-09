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
5. Publish the same `.env` template and `judge_profile_sha256` for the validator set.

Prefer a digest when your registry workflow supports it:

```text
LEAN_SANDBOX_IMAGE=registry.example/lemma/lean-sandbox@sha256:<digest>
```

An immutable version tag is acceptable only when the operator controls the registry policy and will not retag it.

## Updating pins

When Lean or Mathlib changes, update the constants, template, Dockerfile assumptions, generated/frozen catalog metadata, and operator image ref together. Then rebuild the sandbox image, rerun the golden test, publish the new immutable image ref, and announce the cutover block or release tag.

`judge_profile_sha256` includes the configured sandbox image ref and key verification settings. Changing `LEAN_SANDBOX_IMAGE` should therefore change the profile hash operators compare.

Host Lean is for local debugging unless the subnet policy explicitly allows it. If enabled, the host `lake` toolchain must match the published sandbox policy.
