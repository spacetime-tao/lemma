# Toolchain And Image Pinning

Lemma verifies proofs with a specific Lean toolchain, Mathlib revision, and
sandbox image.

These pins affect rewards. Treat them as release artifacts, not local choices.

## Sources Of Truth

| Item | Source |
| --- | --- |
| Default Lean toolchain | [`lemma/catalog/constants.py`](../lemma/catalog/constants.py) |
| Default Mathlib revision | [`lemma/catalog/constants.py`](../lemma/catalog/constants.py) |
| Lean template toolchain file | [`lemma/lean/template/lean-toolchain`](../lemma/lean/template/lean-toolchain) |
| Sandbox image recipe | [`compose/lean.Dockerfile`](../compose/lean.Dockerfile) |
| Runtime image ref | `LEAN_SANDBOX_IMAGE` |

`lemma/lean-sandbox:latest` is a local dev tag. It is not a production pin.

## Production Policy

1. Build the sandbox image from the release checkout.
2. Run the Docker golden test.
3. Publish the image with an immutable tag or digest.
4. Set `LEAN_SANDBOX_IMAGE` to that ref on validators, local-verify miners, and
   Lean workers.
5. Publish the same `.env` template and validator profile hash.

Prefer a digest:

```text
LEAN_SANDBOX_IMAGE=registry.example/lemma/lean-sandbox@sha256:<digest>
```

An immutable version tag is acceptable only if the operator controls the
registry and will not retag it.

## Updating Pins

When Lean or Mathlib changes, update these together:

- constants;
- Lean template;
- Dockerfile assumptions;
- catalog metadata;
- operator image ref.

Then rebuild the sandbox image, rerun the golden test, publish the image, and
announce the cutover block or release tag.

Changing `LEAN_SANDBOX_IMAGE` should change `validator_profile_sha256`.

Host Lean is for local debugging unless subnet policy explicitly allows it.
