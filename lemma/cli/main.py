"""Proof formalization CLI for Lemma."""

from __future__ import annotations

import json
import secrets
from pathlib import Path

import click

from lemma import __version__
from lemma.cli.style import colors_enabled, rich_help_text, stylize
from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging

_PUBLIC_COMMAND_ORDER = ("setup", "mine", "status", "validate")


class LemmaCommand(click.Command):
    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        rich_help = rich_help_text(self, ctx)
        if rich_help is None:
            super().format_help(ctx, formatter)
            return
        formatter.write(rich_help)


class LemmaGroup(click.Group):
    command_class = LemmaCommand
    group_class = type

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        rich_help = rich_help_text(self, ctx)
        if rich_help is None:
            super().format_help(ctx, formatter)
            return
        formatter.write(rich_help)

    def list_commands(self, ctx: click.Context) -> list[str]:
        return [name for name in _PUBLIC_COMMAND_ORDER if name in self.commands]


@click.group(
    name="lemma",
    cls=LemmaGroup,
    invoke_without_command=True,
    context_settings={"max_content_width": 100},
)
@click.pass_context
@click.version_option(version=__version__)
def main(ctx: click.Context) -> None:
    """Lean proof formalization subnet."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help(), color=colors_enabled())


def _env_path(env_path: Path | None) -> Path:
    return env_path or Path.cwd() / ".env"


def _read_submission(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_registry():
    from lemma.bounty.client import BountyError, fetch_registry

    try:
        return fetch_registry(LemmaSettings())
    except (BountyError, OSError) as e:
        raise click.ClickException(str(e)) from e


def _bounty_or_die(bounty_id: str):
    from lemma.bounty.client import BountyError

    registry = _load_registry()
    try:
        return registry, registry.get(bounty_id)
    except BountyError as e:
        raise click.ClickException(str(e)) from e


def _escrow_rows(registry):
    return [bounty for bounty in registry.bounties if bounty.escrow_backed]


def _candidate_rows(registry):
    return [bounty for bounty in registry.bounties if not bounty.escrow_backed]


def _print_bounty_summary(registry) -> None:
    escrow_rows = _escrow_rows(registry)
    candidate_rows = _candidate_rows(registry)
    click.echo(stylize("Lemma proof targets", fg="cyan", bold=True))
    click.echo(stylize(f"registry_sha256={registry.sha256}", dim=True))
    click.echo(stylize("Live rewards require confirmed reward custody rows.\n", dim=True), nl=False)
    if escrow_rows:
        click.echo(stylize("Live targets", fg="cyan"))
        for bounty in escrow_rows:
            click.echo(f"  {stylize(bounty.id, fg='green', bold=True)}  {bounty.title}")
    else:
        click.echo(stylize("No live proof rewards are present in this registry.", fg="yellow", bold=True))
    if candidate_rows:
        click.echo("")
        click.echo(stylize("Candidates", fg="cyan"))
        for bounty in candidate_rows:
            click.echo(f"  {bounty.id}  {bounty.title}")
        click.echo(stylize("\nCandidates are not reward offers until custody is confirmed on-chain.", dim=True))


def _print_bounty_detail(registry, bounty) -> None:
    source_name = bounty.source.get("name") or bounty.source.get("project") or "unknown"
    source_url = bounty.source.get("url")
    click.echo(stylize(bounty.title, fg="cyan", bold=True))
    click.echo(stylize("  id              ", dim=True) + bounty.id)
    click.echo(stylize("  registry_sha256 ", dim=True) + registry.sha256)
    click.echo(stylize("  target_sha256   ", dim=True) + bounty.target_sha256)
    click.echo(stylize("  status          ", dim=True) + bounty.status)
    click.echo(stylize("  source          ", dim=True) + source_name + (f" ({source_url})" if source_url else ""))
    click.echo(stylize("  theorem_id      ", dim=True) + bounty.problem.id)
    click.echo(stylize("  theorem_name    ", dim=True) + bounty.problem.theorem_name)
    click.echo(stylize("  policy          ", dim=True) + bounty.submission_policy)
    if bounty.escrow_backed:
        click.echo(stylize("  custody_contract ", dim=True) + bounty.escrow_contract_address)
        click.echo(stylize("  custody_reward_id", dim=True) + " " + str(bounty.escrow_bounty_id))
    else:
        click.echo(stylize("  custody         not funded/confirmed", fg="yellow"))
    click.echo("")
    click.echo(stylize("Lean target", fg="cyan", bold=True))
    click.echo(bounty.problem.submission_stub().rstrip())


def _hotkey_public_key_hex(settings: LemmaSettings, wallet_cold: str | None, wallet_hot: str | None) -> str:
    import bittensor as bt

    wallet = bt.Wallet(name=wallet_cold or settings.wallet_cold, hotkey=wallet_hot or settings.wallet_hot)
    pub = getattr(wallet.hotkey, "public_key", None)
    if callable(pub):
        pub = pub()
    if isinstance(pub, bytes):
        return "0x" + pub.hex()
    raw = str(pub or "").strip()
    if raw.startswith("0x") and len(raw) == 66:
        return raw
    raise click.ClickException("Could not read the hotkey public key for payout identity binding.")


def _sign_bounty_identity(
    settings: LemmaSettings,
    *,
    wallet_cold: str | None,
    wallet_hot: str | None,
    message: bytes,
) -> str:
    import bittensor as bt

    wallet = bt.Wallet(name=wallet_cold or settings.wallet_cold, hotkey=wallet_hot or settings.wallet_hot)
    return wallet.hotkey.sign(message).hex()


def _bounty_escrow_values(settings: LemmaSettings, bounty) -> tuple[int, str, int]:
    chain_id = bounty.escrow_chain_id or int(settings.bounty_evm_chain_id)
    contract = bounty.escrow_contract_address or (settings.bounty_escrow_contract_address or "").strip()
    escrow_bounty_id = bounty.escrow_bounty_id
    if not contract or escrow_bounty_id is None:
        raise click.ClickException(
            "This target has no confirmed reward custody. Live rewards require custody metadata.",
        )
    return int(chain_id), contract, int(escrow_bounty_id)


@main.command("setup")
@click.option("--env-file", "env_path", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.option("--registry-url", default=None, help="Proof target registry JSON URL or path.")
@click.option("--registry-sha256", default=None, help="Optional registry SHA256 pin.")
@click.option("--escrow-contract", default=None, help="Deployed LemmaBountyEscrow custody contract address.")
@click.option("--evm-rpc-url", default=None, help="Bittensor EVM JSON-RPC URL.")
@click.option("--evm-chain-id", type=int, default=None, help="Bittensor EVM chain id.")
@click.option("--wallet-cold", default=None, help="Bittensor cold wallet name for hotkey signatures.")
@click.option("--wallet-hot", default=None, help="Bittensor hotkey name for signatures.")
def setup_cmd(
    env_path: Path | None,
    registry_url: str | None,
    registry_sha256: str | None,
    escrow_contract: str | None,
    evm_rpc_url: str | None,
    evm_chain_id: int | None,
    wallet_cold: str | None,
    wallet_hot: str | None,
) -> None:
    """Write local target registry and reward custody settings."""
    from lemma.cli.env_file import merge_dotenv

    updates = {
        "LEMMA_BOUNTY_REWARD_CUSTODY": "evm_escrow",
        "LEMMA_BOUNTY_REGISTRY_URL": registry_url or LemmaSettings.model_fields["bounty_registry_url"].default,
        "LEMMA_BOUNTY_EVM_RPC_URL": evm_rpc_url or LemmaSettings.model_fields["bounty_evm_rpc_url"].default,
        "LEMMA_BOUNTY_EVM_CHAIN_ID": str(evm_chain_id or LemmaSettings.model_fields["bounty_evm_chain_id"].default),
        "BT_WALLET_COLD": wallet_cold or LemmaSettings.model_fields["wallet_cold"].default,
        "BT_WALLET_HOT": wallet_hot or LemmaSettings.model_fields["wallet_hot"].default,
    }
    if registry_sha256:
        updates["LEMMA_BOUNTY_REGISTRY_SHA256_EXPECTED"] = registry_sha256
    if escrow_contract:
        updates["LEMMA_BOUNTY_ESCROW_CONTRACT_ADDRESS"] = escrow_contract
    path = _env_path(env_path)
    merge_dotenv(path, {key: str(value) for key, value in updates.items()})
    click.echo(stylize(f"Wrote {path}", fg="green", bold=True))


@main.command("status")
def status_cmd() -> None:
    """Show proof target registry and reward custody status."""
    settings = LemmaSettings()
    click.echo(stylize("Lemma proof status", fg="cyan", bold=True))
    click.echo(stylize("  custody         ", dim=True) + settings.bounty_reward_custody)
    click.echo(stylize("  evm_chain_id    ", dim=True) + str(settings.bounty_evm_chain_id))
    click.echo(stylize("  evm_rpc_url     ", dim=True) + settings.bounty_evm_rpc_url)
    click.echo(
        stylize("  custody_contract", dim=True)
        + " "
        + ((settings.bounty_escrow_contract_address or "").strip() or "not configured"),
    )
    click.echo("")
    _print_bounty_summary(_load_registry())


@main.command("mine")
@click.argument("bounty_id", required=False, metavar="TARGET_ID")
@click.option("--submission", "submission_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--commit", "make_commit", is_flag=True, help="Build a custody commit transaction package.")
@click.option("--reveal", "make_reveal", is_flag=True, help="Build a custody reveal transaction package.")
@click.option("--artifact-uri", default="", help="Public URI for the proof artifact; included in reveal metadata.")
@click.option("--claimant-evm", default="", help="EVM address that sends the custody transaction.")
@click.option("--payout-evm", default="", help="EVM address that receives the reward payout.")
@click.option("--salt", default="", help="32-byte hex salt. Required for --reveal; random default for --commit.")
@click.option("--wallet-cold", default=None, help="Cold wallet name for hotkey identity binding.")
@click.option("--wallet-hot", default=None, help="Hotkey name for identity binding.")
@click.option("--host-lean", "host_lean", is_flag=True, default=False)
@click.option("--output", "output_path", type=click.Path(dir_okay=False, path_type=Path), default=None)
def mine_cmd(
    bounty_id: str | None,
    submission_path: Path | None,
    make_commit: bool,
    make_reveal: bool,
    artifact_uri: str,
    claimant_evm: str,
    payout_evm: str,
    salt: str,
    wallet_cold: str | None,
    wallet_hot: str | None,
    host_lean: bool,
    output_path: Path | None,
) -> None:
    """Verify a Lean proof and build payout transaction data."""
    from lemma.bounty.client import BountyError, verify_bounty_proof
    from lemma.bounty.escrow import (
        EscrowError,
        bounty_identity_binding_message,
        build_commitment,
        bytes32_from_text,
        encode_commit_proof_call,
        encode_reveal_proof_call,
        proof_artifact_sha256,
    )

    if make_commit and make_reveal:
        raise click.UsageError("Use --commit or --reveal, not both.")

    registry = _load_registry()
    if not bounty_id:
        _print_bounty_summary(registry)
        return
    try:
        bounty = registry.get(bounty_id)
    except BountyError as e:
        raise click.ClickException(str(e)) from e

    settings = LemmaSettings()
    chain_id, contract, escrow_bounty_id = _bounty_escrow_values(settings, bounty)
    _print_bounty_detail(registry, bounty)
    if submission_path is None:
        click.echo("")
        click.echo(
            stylize("Next: ", dim=True)
            + stylize(f"lemma mine {bounty.id} --submission Submission.lean", fg="green")
        )
        return

    proof_script = _read_submission(submission_path)
    try:
        result = verify_bounty_proof(settings, bounty, proof_script, host_lean=host_lean)
    except BountyError as e:
        raise click.ClickException(str(e)) from e
    click.echo("")
    click.echo(result.model_dump_json(indent=2))
    if not result.passed:
        raise SystemExit(1)
    if not (make_commit or make_reveal):
        click.echo(
            stylize(
                "Proof verifies locally. Add --commit or --reveal to build payout transaction data.",
                fg="green",
            )
        )
        return
    if not claimant_evm or not payout_evm:
        raise click.UsageError("--claimant-evm and --payout-evm are required for payout packages.")
    if make_reveal and not salt.strip():
        raise click.UsageError("--salt is required for --reveal.")

    artifact_hash = "0x" + proof_artifact_sha256(submission_path)
    salt_hex = salt.strip() or "0x" + secrets.token_hex(32)
    try:
        hotkey_pubkey = _hotkey_public_key_hex(settings, wallet_cold, wallet_hot)
        commitment = build_commitment(
            bounty_id=bounty.id,
            chain_id=chain_id,
            contract_address=contract,
            escrow_bounty_id=escrow_bounty_id,
            theorem_id=bytes32_from_text(bounty.problem.id),
            claimant_evm_address=claimant_evm,
            payout_evm_address=payout_evm,
            artifact_sha256=artifact_hash,
            salt=salt_hex,
            toolchain_id=bytes32_from_text(bounty.toolchain_id),
            policy_version=bytes32_from_text(bounty.policy_version),
            registry_sha256="0x" + registry.sha256,
            submitter_hotkey_pubkey=hotkey_pubkey,
        )
        binding_msg = bounty_identity_binding_message(
            bounty_id=bounty.id,
            registry_sha256="0x" + registry.sha256,
            claimant_evm_address=claimant_evm,
            payout_evm_address=payout_evm,
            artifact_sha256=artifact_hash,
            commitment_hash_hex=commitment.commitment_hash,
        )
        signature_hex = _sign_bounty_identity(
            settings,
            wallet_cold=wallet_cold,
            wallet_hot=wallet_hot,
            message=binding_msg,
        )
    except EscrowError as e:
        raise click.ClickException(str(e)) from e

    package = commitment.as_dict()
    package["identity_binding_signature_hex"] = signature_hex
    package["artifact_uri"] = artifact_uri.strip()
    if make_commit:
        package["transaction"] = {
            "to": contract,
            "data": encode_commit_proof_call(escrow_bounty_id, commitment.commitment_hash),
            "value": "0x0",
        }
    else:
        package["transaction"] = {
            "to": contract,
            "data": encode_reveal_proof_call(
                escrow_bounty_id=escrow_bounty_id,
                commitment_hash_hex=commitment.commitment_hash,
                artifact_sha256=artifact_hash,
                salt=salt_hex,
                payout_evm_address=payout_evm,
                submitter_hotkey_pubkey=hotkey_pubkey,
            ),
            "value": "0x0",
        }
    text = json.dumps(package, indent=2, sort_keys=True)
    if output_path:
        output_path.write_text(text + "\n", encoding="utf-8")
        click.echo(stylize(f"Wrote {output_path}", fg="green", bold=True))
    else:
        click.echo(text)


@main.command("validate")
@click.option("--check", is_flag=True, help="Check target registry and reward custody configuration.")
@click.option("--once", is_flag=True, help="Run one local readiness pass; no event watcher is bundled.")
@click.option("--worker", is_flag=True, help="Run the Lean verification HTTP worker.")
@click.option("--host", default="localhost", show_default=True, help="Worker bind host.")
@click.option("--port", default=8787, type=int, show_default=True, help="Worker bind port.")
def validate_cmd(check: bool, once: bool, worker: bool, host: str, port: int) -> None:
    """Validate proof verifier readiness or run the Lean worker."""
    settings = LemmaSettings()
    setup_logging(settings.log_level)
    if worker:
        from lemma.lean.worker_http import serve_forever

        serve_forever(host, port, settings)
        return

    registry = _load_registry()
    escrow_rows = _escrow_rows(registry)
    if not (settings.bounty_escrow_contract_address or "").strip() and not escrow_rows:
        raise click.ClickException("No custody contract is configured and no registry row has confirmed custody.")
    click.echo(stylize("Lemma validate", fg="cyan", bold=True))
    click.echo(stylize("  registry_sha256 ", dim=True) + registry.sha256)
    click.echo(stylize("  custody_rows    ", dim=True) + str(len(escrow_rows)))
    if check:
        click.echo(stylize("READY: target registry and custody settings are present.", fg="green"))
        return
    if once:
        click.echo(stylize("No reveal-event watcher is bundled in this refactor.", fg="yellow"))
        click.echo(
            stylize(
                "Verifier signers should fetch revealed artifacts, run Lean verification, then attest on-chain.",
                dim=True,
            )
        )
        return
    click.echo(
        stylize("Use --check for preflight, --once for a readiness pass, or --worker to serve /verify.", dim=True)
    )
