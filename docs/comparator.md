# Comparator Hook

This is an **experimental, default-off** post-verify hook.

After `lake build`, axiom checks, and cheat scans pass, Lemma can run one operator-supplied command with the verified workspace as its current directory. The repo does **not** ship [leanprover/comparator](https://github.com/leanprover/comparator), a production comparator policy, or [lean-eval](https://github.com/leanprover/lean-eval) isolation.

Default policy: leave this off. Kernel checking plus the axiom policy are the v1 verification floor.

| Variable | Purpose |
| -------- | ------- |
| `LEMMA_COMPARATOR_ENABLED` | Process env only; enable with `1`, `true`, or `yes` |
| `LEMMA_COMPARATOR_CMD` | Process env only; command parsed with `shlex.split` and run without a shell |
| `LEMMA_COMPARATOR_TIMEOUT_S` | Process env only; optional, default 120 |

If enabled, every validator that scores the subnet must run the exact same command and timeout policy. These fields are **not** currently included in `judge_profile_sha256`, so parity has to come from the published operator deployment template.

Non-zero exit, command errors, or timeout return `comparator_rejected` ([`VerifyResult`](../lemma/lean/sandbox.py)). For remote Lean verification, the hook runs on the Lean worker process, not on the validator process.
