# Comparator (optional)

After successful **`lake build`** and axiom checks, an optional shell command may run in the same workspace (host or container paths).

Enables integration of [leanprover/comparator](https://github.com/leanprover/comparator) or custom checks. Disabled unless configured.

- **Default:** off — kernel + axiom policy cover v1 security.
- **If enabled on a subnet:** all validators must use the same **`LEMMA_COMPARATOR_CMD`** (or disable everywhere) to keep scores comparable.

| Variable | Purpose |
| -------- | ------- |
| `LEMMA_COMPARATOR_ENABLED` | `1` / `true` / `yes` |
| `LEMMA_COMPARATOR_CMD` | Shell command (e.g. `shlex` list) |
| `LEMMA_COMPARATOR_TIMEOUT_S` | Optional (default 120) |

Non-zero exit → **`comparator_rejected`** ([`VerifyResult`](../lemma/lean/sandbox.py)). Full [lean-eval](https://github.com/leanprover/lean-eval) isolation is not shipped here.
