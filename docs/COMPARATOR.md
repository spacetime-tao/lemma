# Comparator (optional)

After successful `lake build` and axiom checks, an optional shell command may run in the same workspace.

Integrates [leanprover/comparator](https://github.com/leanprover/comparator) or custom checks. Off unless configured.

- Default: off — kernel + axiom policy cover v1.
- If enabled on a subnet: all validators must share `LEMMA_COMPARATOR_CMD` (or disable everywhere).

| Variable | Purpose |
| -------- | ------- |
| `LEMMA_COMPARATOR_ENABLED` | `1` / `true` / `yes` |
| `LEMMA_COMPARATOR_CMD` | Shell command |
| `LEMMA_COMPARATOR_TIMEOUT_S` | Optional (default 120) |

Non-zero exit → `comparator_rejected` ([`VerifyResult`](../lemma/lean/sandbox.py)). Full [lean-eval](https://github.com/leanprover/lean-eval) isolation is not shipped here.
