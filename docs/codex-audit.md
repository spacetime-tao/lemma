# Lemma codebase audit (Codex assessment)

This document records a docs-only engineering and security posture review of the
Lemma repository ([github.com/spacetime-tao/lemma](https://github.com/spacetime-tao/lemma)),
produced with Codex. It is not a penetration test, formal verification of the
Python stack, or an independent third-party security audit.

The review lens was deliberately strict: **treat every line of code as a
liability**. A line should justify itself by reducing risk, clarifying the
system, or making invalid states harder to express.

---

## Rating

**7.2 / 10** - **B engineering quality** for an early-stage Bittensor subnet.
For adversarial production readiness alone, the rating is **C+ to B-**.

This mostly aligns with the Cursor audit's **7.5 / 10**, but Codex rates the
repo slightly lower because a few remaining surfaces still add operational or
adversarial risk without enough hard edges in code.

| Dimension | Score (0-10) | Comment |
| --- | ---: | --- |
| Architecture and clarity | 8.0 | The module split is understandable: protocol, miner, validator, Lean verification, scoring, CLI, docs. |
| Proof-only mechanism fit | 7.5 | The live eligibility path is coherent: Lean pass enters scoring, Lean fail does not. Post-pass reputation and partitioning still mean final weights are not purely equal-per-pass. |
| Testing and CI | 8.0 | Ruff, mypy, pytest, pip-audit, bandit medium/high, and generated-template metadata checks are wired into CI. |
| Security posture | 7.0 | Good awareness of Docker, pins, body hashes, and remote verifier risk; still has sharp ops edges around Docker socket, remote workers, and dependency inheritance. |
| Line liability / simplicity | 6.5 | The proof-only path is much cleaner than the older judge-heavy direction, but optional judge/proof-metric/reputation surfaces still make the repo carry more policy weight than the core objective needs. |

---

## Alignment with Cursor

Codex agrees with Cursor's broad verdict:

1. The codebase is unusually disciplined for an early subnet implementation.
2. The proof-verification path is clear and test-covered.
3. CI security automation is real, not just a checklist.
4. Docker, remote Lean workers, Bittensor economics, and dependencies remain the largest production risks.
5. This repo should not be treated as externally audited for high-value mainnet operation.

The difference is emphasis. Cursor graded the repo as a strong early-stage
implementation. Codex also asks whether each line and knob helps the simple
goal: **valid Lean proof passes, invalid proof fails**. Under that lens, a few
remaining surfaces deserve a more conservative score.

---

## Codex-only findings

1. **Validator response size cap is asymmetric.**

   The audit found miner-side `SYNAPSE_MAX_PROOF_CHARS` enforcement without a
   matching validator inbound check. Status: fixed after the audit; the shared
   synapse limit now rejects oversized `resp.proof_script` payloads in the
   validator epoch path before verification work is queued.

2. **Remote Lean worker defaults are permissive.**

   The audit found that `lemma lean-worker` accepted `/verify` without
   authentication when `LEMMA_LEAN_VERIFY_REMOTE_BEARER` was unset. Status:
   fixed after the audit; non-loopback worker binds now require bearer auth
   unless the operator sets the explicit dev-only unauthenticated override.

3. **Binary eligibility is simple; final weights are not purely binary.**

   `entry_from_verified_proof()` assigns every verified proof `score=1.0` and
   `cost=0`, which preserves the proof-pass eligibility rule. After that,
   reputation/credibility EMA, Pareto layering, and same-coldkey partitioning can
   alter final weights. This may be intended economics, but the docs and future
   mechanism work should keep saying the precise thing: **proof verification is
   binary; downstream allocation policy is additional policy**.

4. **Tracker drift was real.**

   Before this audit-doc pass, `local handoff note` and `docs/workplan.md` still
   described an older head, old failing CI context, and old mypy failures. The
   source tree itself was clean, but stale status files can mislead future
   agents into fixing already-fixed problems.

5. **Full Bandit still reports low-severity noise.**

   CI correctly gates only medium/high Bandit findings with `-ll`, and that gate
   passed. A full local Bandit run still reports low-severity items around
   subprocess use, seeded RNG for deterministic problem selection, `assert`, and
   broad cleanup exceptions. Most are explainable in context, but they are still
   useful line-liability cleanup candidates.

---

## Verification run

Verified against local/GitHub `main` at:

```text
28bbbfc8c747c46ff5d6c5b0e015e5451aeb4e58
```

Commands and results recorded during the Codex audit:

| Check | Result |
| --- | --- |
| `.venv/bin/ruff check lemma tests tools` | Passed. |
| `.venv/bin/mypy lemma` | Passed: `Success: no issues found in 68 source files`. |
| `.venv/bin/pytest tests -q` | Passed: `254 passed, 2 skipped, 12 warnings`. |
| `.venv/bin/python scripts/ci_verify_generated_templates.py` | Passed metadata gate: `OK: generated template metadata gate covered 40 builders`; Docker template compile skipped because `RUN_DOCKER_LEAN_TEMPLATES=1` was not set. |
| `.venv/bin/bandit -q -r lemma -ll` | Passed: no medium/high findings. |
| `.venv/bin/bandit -q -r lemma` | Failed only on 24 low-severity findings. |
| `.venv/bin/pip-audit --ignore-vuln PYSEC-2025-49 --ignore-vuln PYSEC-2022-42969` | Passed with `No known vulnerabilities found, 3 ignored`; local package `lemma` is not on PyPI and could not be audited as a PyPI dependency. |
| Docker Lean golden | Not rerun locally; Docker daemon was unavailable at the local socket. |

---

## Recommended fix order

1. Keep binary proof eligibility language precise, especially where docs discuss
   reputation, credibility, Pareto weighting, and same-coldkey partitioning.
2. Retire or isolate optional judge/proof-metric research code when it stops
   paying for its maintenance cost.
3. Work through low-severity Bandit noise only when the fix removes ambiguity or
   code, not by scattering defensive wrappers.

---

## Summary verdict

Lemma is in good shape for a proof-of-concept subnet and has a much cleaner
incentive story after the proof-only pivot. The live path now mostly honors the
simple rule: **pass or fail, binary system**. The remaining downgrade comes from
operational attack surface and policy surface, not from a broken core proof
checker story.

For the next engineering pass, resist adding new layers. The highest-value work
is to tighten boundaries where invalid or expensive states currently enter, and
to delete surfaces that no longer serve the proof-only mechanism.
