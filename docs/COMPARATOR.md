# Comparator hook (experimental)

After Lean **`lake build`** and axiom checks succeed, you can run an **optional** shell command inside the same temporary workspace (host or Docker-side equivalent paths).

This is a **placeholder** for integrating tools such as [leanprover/comparator](https://github.com/leanprover/comparator) or custom scripts that compare statements/proofs. Nothing runs unless explicitly enabled.

## Should we use it?

- **Default recommendation: no.** Kernel checking and axiom rules already decide whether a proof is acceptable for Lemma’s main security story. The comparator adds **ops burden** and another moving part.
- **Use it when** your subnet explicitly wants **stronger statement equivalence** or **extra tooling** beyond `lake build` (policy decision—document it in subnet governance).
- **If any validator enables it, every validator on that subnet should use the same** `LEMMA_COMPARATOR_ENABLED` / `LEMMA_COMPARATOR_CMD`. Mixed deployments ⇒ incomparable scores (same reasoning as pinning one judge stack).

## Environment

| Variable | Meaning |
| -------- | ------- |
| `LEMMA_COMPARATOR_ENABLED` | Set to `1` / `true` / `yes` to enable |
| `LEMMA_COMPARATOR_CMD` | Shell tokenization via `shlex` (e.g. `/usr/local/bin/my-check --workspace .`) |
| `LEMMA_COMPARATOR_TIMEOUT_S` | Optional cap (default `120`) |

If the command exits non-zero, verification fails with reason **`comparator_rejected`** (see [`VerifyResult`](../lemma/lean/sandbox.py)).

## Production note

Full **landrun** / isolation parity with [lean-eval](https://github.com/leanprover/lean-eval) is **not** bundled here; wire your binary and security model according to subnet policy.
