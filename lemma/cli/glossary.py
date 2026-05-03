"""Short CLI glossary (terms used in status, seeds, try-prover)."""

from __future__ import annotations

import click

from lemma.cli.style import stylize


def print_glossary() -> None:
    """Echo glossary to stdout."""
    click.echo(stylize("Lemma glossary", fg="cyan", bold=True))
    click.echo(stylize("(quick definitions — see docs/FAQ.md for detail)\n", dim=True), nl=False)

    sections: tuple[tuple[str, str], ...] = (
        (
            "lemma problems (two words after lemma)",
            "`lemma problems` alone prints the **current** challenge (same as `lemma problems show --current`).\n"
            "  • lemma problems show --block N — pretend chain head is N (what-if / countdown from N)\n"
            "  • lemma problems show <theorem_id> — one catalog row by id (fixed id, not live rotation)\n"
            "  • lemma problems list — frozen catalog only when LEMMA_PROBLEM_SOURCE=frozen\n"
            "There is no `lemma problems --list`; use the word `list` as a subcommand.",
        ),
        (
            "`lemma problems show` output",
            "Yellow **View:** line — live vs simulated head vs fixed id. "
            "chain_head — block height used for this draw (`--current` uses live RPC head).\n"
            "problem_seed — number fed into the generated template; same head + NETUID + seed mode ⇒ same theorem "
            "for all validators.\n"
            "seed_tag — how that seed was computed (e.g. subnet_epoch vs quantize; see LEMMA_PROBLEM_SEED_MODE).\n"
            "Theorem — id, name, area, difficulty, builder: catalog metadata. Lean goal — the formal statement "
            "to prove.\n"
            "Challenge.lean — what validators send miners: Mathlib import, theorem declaration ending with `sorry` "
            "(your job is to replace sorry with a proof).",
        ),
        (
            "LEMMA_PROBLEM_SEED_MODE / quantize_blocks",
            "How chain height becomes problem_seed so **validators agree on the same theorem**.\n"
            "  • subnet_epoch (default) — Tempo-aligned; same chain head + NETUID ⇒ same seed.\n"
            "  • quantize — uses LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS=N in the formula.\n"
            "`lemma status` only shows quantize_blocks when mode is quantize (otherwise it’s irrelevant noise).",
        ),
        (
            "try-prover vs try-prover --verify",
            "Both paths ask the LLM for **text**: reasoning plus the contents of Submission.lean as a **string**.\n"
            "Running `lemma try-prover` in a terminal prompts once before billing your API (`--yes` skips it; "
            "the numbered START HERE menu skips it because you already picked the step).\n"
            "That output is **not** the same as Lean successfully **building** that file (imports, Mathlib, proofs).\n"
            "`--verify` runs a local Lean build (Docker/host) to see if that script actually compiles — "
            "similar *idea* to the validator’s Lean step, but only on your machine.\n"
            "It does **not** run the LLM **judge** (scores). Validators still run Lean + judge themselves.",
        ),
        (
            "miner-dry vs miner",
            "miner-dry (or miner --dry-run) prints axon-related settings only — no HTTP server, no API spend.\n"
            "miner starts the real axon so validators can forward challenges (prover bills when answering).",
        ),
        (
            "validator-dry vs validator",
            "validator-dry prints a one-shot summary of validator-related env (wallet, timeouts, …).\n"
            "validator runs the full scoring loop; use validator --dry-run for repeated rounds without set_weights.",
        ),
        (
            "validator-check",
            "Run **before** `lemma validator`: chain RPC, UID for **validator** wallet on NETUID (see "
            "BT_VALIDATOR_WALLET_* vs BT_WALLET_*), optional pin drift vs `lemma meta`, Lean image. "
            "READY or NOT READY — unlike validator-dry, which only prints env.",
        ),
        (
            "Validator wallet vs miner",
            "Miner axon uses BT_WALLET_COLD / BT_WALLET_HOT. If you use different keys to validate, set "
            "BT_VALIDATOR_WALLET_COLD and BT_VALIDATOR_WALLET_HOT; otherwise the validator reuses the miner names.",
        ),
        (
            "How often does the theorem change?",
            "Default **quantize** mode: everyone sees the same theorem for "
            "`LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS` (default 100 blocks ≈ 20 min at 12 s/block). "
            "`lemma status` shows **time left** until the next theorem in plain language.",
        ),
        (
            "Forward HTTP wait vs LEMMA_LLM_HTTP_TIMEOUT_S",
            "Validator **forward wait** = HTTP timeout for one axon answer: remaining blocks in the window × "
            "LEMMA_BLOCK_TIME_SEC_ESTIMATE, clamped by LEMMA_FORWARD_WAIT_MIN_S / LEMMA_FORWARD_WAIT_MAX_S. "
            "LLM **wait** = one prover API call (LEMMA_LLM_HTTP_TIMEOUT_S). Keep LLM within that forward wait. "
            "Synapse **deadline_block** is the chain height after which the answer is late.",
        ),
        (
            "Subnet hash pins (`lemma configure subnet-pins`)",
            "Writes expected-hash lines into `.env` copied from `lemma meta`. Optional safety only — "
            "does not block running a validator unless you turn on LEMMA_VALIDATOR_ENFORCE_PUBLISHED_META=1.",
        ),
        (
            "Can I run a validator?",
            "Use `lemma validator-check` for a clear pre-flight (READY / NOT READY). Usually you’re fine if: "
            "RPC works, hotkey has a UID on NETUID, judge API keys set, Lean image present, timeouts OK "
            "(`lemma doctor` for key/env sanity). Pins in `.env` are optional; without ENFORCE they don’t stop "
            "startup. If something “doesn’t match,” compare **live** `lemma meta` to your pinned expected lines "
            "— or remove pins until you understand them.",
        ),
    )
    for title, body in sections:
        click.echo(stylize(title, fg="cyan"))
        click.echo(stylize(body, dim=True))
        click.echo("")
