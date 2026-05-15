"""Manual-proof miner axon lifecycle."""

import json
import time
from typing import Any, Tuple, cast  # noqa: UP035
from urllib.parse import urljoin
from urllib.request import urlopen

import bittensor as bt
import click
from loguru import logger

from lemma.cli.style import stylize
from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging
from lemma.common.subtensor import get_subtensor
from lemma.common.synapse_limits import synapse_payload_error
from lemma.ledger import matching_solved_ledger
from lemma.lifecycle import target_phase
from lemma.miner.forward import make_forward
from lemma.problems.factory import get_problem_source
from lemma.protocol import LemmaChallenge
from lemma.submissions import load_pending_submissions, resolved_submissions_path


def _current_phase(settings: LemmaSettings, subtensor):
    source = get_problem_source(settings)
    hashes = {problem.id: problem.theorem_statement_sha256() for problem in source.all_problems()}
    ledger = matching_solved_ledger(settings.solved_ledger_path, hashes)
    return target_phase(settings, ledger, int(subtensor.get_current_block()))


def _status_line(label: str, message: str, *, fg: str) -> None:
    click.echo(stylize(f"{label:<12}", fg=fg, bold=True) + message, err=True)


def _poll_eta(settings: LemmaSettings) -> str:
    minutes = max(1, round(float(settings.validator_poll_interval_s) / 60))
    return f"validators poll about every {minutes} min after reveal, then run Lean"


def _dashboard_json_url(settings: LemmaSettings) -> str:
    url = str(settings.public_dashboard_url).strip()
    if url.endswith(".json"):
        return url
    return urljoin(url.rstrip("/") + "/", "/data/miner-dashboard.json")


def _public_dashboard(settings: LemmaSettings) -> dict[str, Any] | None:
    try:
        with urlopen(_dashboard_json_url(settings), timeout=5) as response:  # noqa: S310
            data = json.loads(response.read().decode("utf-8"))
            return cast(dict[str, Any], data) if isinstance(data, dict) else None
    except Exception as exc:  # noqa: BLE001
        logger.debug("public dashboard unavailable: {}", exc)
        return None


def _dashboard_acceptances(
    data: dict[str, Any] | None,
    *,
    miner_hotkey: str,
    proof_hashes: set[str],
) -> list[dict[str, Any]]:
    if not data or not proof_hashes:
        return []
    active = data.get("active_target")
    next_target = None
    if isinstance(active, dict):
        next_target = active.get("id") or active.get("theorem_name") or active.get("title")
    accepted: list[dict[str, Any]] = []
    for receipt in data.get("accepted_proof_receipts") or []:
        if not isinstance(receipt, dict):
            continue
        proof_hash = str(receipt.get("proof_sha256") or "")
        if receipt.get("solver_hotkey") == miner_hotkey and proof_hash in proof_hashes:
            accepted.append(
                {
                    "target_id": receipt.get("target_id") or "unknown target",
                    "solver_uid": receipt.get("solver_uid"),
                    "proof_sha256": proof_hash,
                    "next_target": next_target,
                },
            )
    return accepted


def _miner_blacklist(settings: LemmaSettings):
    def blacklist(synapse: LemmaChallenge) -> Tuple[bool, str]:  # noqa: UP006
        err = synapse_payload_error(synapse, settings, response=False)
        return (err is not None, err or "")

    return blacklist


def _zero_priority(synapse: LemmaChallenge) -> float:
    return 0.0


class MinerService:
    def __init__(self, settings: LemmaSettings | None = None) -> None:
        self.settings = settings or LemmaSettings()

    def run(self) -> None:
        setup_logging(self.settings.log_level)
        s = self.settings
        wallet = bt.Wallet(name=s.wallet_cold, hotkey=s.wallet_hot)
        subtensor = get_subtensor(s)

        external_ip = (s.axon_external_ip or "").strip() or None
        if external_ip is None:
            logger.warning("AXON_EXTERNAL_IP is unset; set it explicitly if validators cannot reach this miner")

        axon = bt.Axon(wallet=wallet, port=s.axon_port, external_ip=external_ip)
        axon.attach(forward_fn=make_forward(s), blacklist_fn=_miner_blacklist(s), priority_fn=_zero_priority)
        axon.serve(netuid=s.netuid, subtensor=subtensor)
        axon.start()

        pending = load_pending_submissions(s.miner_submissions_path)
        try:
            phase = _current_phase(s, subtensor)
            logger.info(
                "Target lifecycle phase={} current_block={} reveal_block={} blocks_until_reveal={}",
                phase.name,
                phase.current_block,
                phase.reveal_block,
                phase.blocks_until_reveal,
            )
            if phase.name == "commit":
                _status_line(
                    "COMMIT",
                    f"proof is private until reveal block {phase.reveal_block}",
                    fg="yellow",
                )
                logger.info("Commit phase: miner will not reveal proof text until block {}.", phase.reveal_block)
            elif phase.name == "reveal":
                _status_line("REVEAL OPEN", "proof is available to validators now", fg="green")
                logger.info("Reveal phase: committed proofs are safe to serve to validators now.")
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Target lifecycle unavailable; miner will not reveal proofs until it can resolve phase: {}",
                exc,
            )
        logger.info(
            "Manual-proof miner listening netuid={} port={} hotkey={} submissions={} store={}",
            s.netuid,
            s.axon_port,
            wallet.hotkey.ss58_address,
            len(pending),
            resolved_submissions_path(s.miner_submissions_path),
        )
        logger.info(
            "Keep miner running until your UID appears on {} or in `lemma target ledger` "
            "if you have the validator/operator ledger locally.",
            s.public_dashboard_url,
        )
        logger.info(
            "Wait hint: validator poll interval is about {}s, plus Lean verify time.",
            int(s.validator_poll_interval_s),
        )
        _status_line(
            "MINER LIVE",
            "waiting for validators; keep this open until your UID appears on the dashboard",
            fg="cyan",
        )
        _status_line("ETA", _poll_eta(s), fg="magenta")
        _status_line("DASHBOARD", s.public_dashboard_url, fg="bright_blue")
        _status_line("LEDGER", "lemma target ledger (local validator/operator ledger)", fg="cyan")
        logger.info("Miner running - Ctrl+C to stop.")
        try:
            started = time.monotonic()
            announced_acceptance: set[tuple[str, str]] = set()
            proof_hashes = {entry.proof_sha256 for entry in pending.values() if entry.proof_sha256}
            while True:
                time.sleep(60)
                elapsed = int(time.monotonic() - started)
                try:
                    phase = _current_phase(s, subtensor)
                    if phase.name == "commit":
                        _status_line(
                            "WAITING",
                            f"commit phase, {phase.blocks_until_reveal} blocks until reveal; {_poll_eta(s)}",
                            fg="yellow",
                        )
                        logger.info(
                            "Miner still running elapsed={}s phase=commit current_block={} reveal_block={} "
                            "blocks_until_reveal={}; proof is still private.",
                            elapsed,
                            phase.current_block,
                            phase.reveal_block,
                            phase.blocks_until_reveal,
                        )
                    else:
                        acceptances = _dashboard_acceptances(
                            _public_dashboard(s),
                            miner_hotkey=wallet.hotkey.ss58_address,
                            proof_hashes=proof_hashes,
                        )
                        announced_now = False
                        for accepted in acceptances:
                            key = (str(accepted["target_id"]), str(accepted["proof_sha256"]))
                            if key not in announced_acceptance:
                                announced_now = True
                                announced_acceptance.add(key)
                                next_target = accepted.get("next_target") or "all listed targets are solved"
                                uid = accepted.get("solver_uid") or "unknown"
                                _status_line(
                                    "ACCEPTED",
                                    f"UID {uid} solved {accepted['target_id']}; next theorem {next_target}",
                                    fg="green",
                                )
                                _status_line(
                                    "NEXT",
                                    f"stop this miner, then run lemma mine for {next_target}",
                                    fg="cyan",
                                )
                                logger.info(
                                    "Proof accepted target_id={} solver_uid={} proof_sha256={} next_target={}",
                                    accepted["target_id"],
                                    uid,
                                    accepted["proof_sha256"],
                                    next_target,
                                )
                        if not acceptances:
                            _status_line(
                                "WAITING",
                                f"proof ready, not accepted yet; next poll can take about "
                                f"{max(1, round(float(s.validator_poll_interval_s) / 60))} min + Lean",
                                fg="green",
                            )
                            logger.info(
                                "Waiting for validator poll elapsed={}s current_block={}; proof is ready to serve, "
                                "but acceptance is not confirmed until your UID appears on {} "
                                "or in `lemma target ledger`.",
                                elapsed,
                                phase.current_block,
                                s.public_dashboard_url,
                            )
                        elif not announced_now:
                            next_target = acceptances[0].get("next_target") or "all listed targets are solved"
                            _status_line(
                                "ACCEPTED",
                                f"already confirmed; stop this miner, then run lemma mine for {next_target}",
                                fg="green",
                            )
                except Exception as exc:  # noqa: BLE001
                    logger.info(
                        "Miner still running elapsed={}s; phase unavailable: {}. Stop after your UID appears on {} "
                        "or in `lemma target ledger` if you have the validator/operator ledger locally.",
                        elapsed,
                        exc,
                        s.public_dashboard_url,
                    )
        except KeyboardInterrupt:
            logger.info("Miner shutting down")
            axon.stop()
