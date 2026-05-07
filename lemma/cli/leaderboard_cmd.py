"""Metagraph leaderboard for operators."""

from __future__ import annotations

import click

from lemma.cli.style import stylize
from lemma.common.config import LemmaSettings
from lemma.common.subtensor import get_subtensor


def _float_at(obj: object, uid: int) -> float:
    raw = obj[uid]  # type: ignore[index]
    try:
        return float(raw.item())  # type: ignore[union-attr]
    except Exception:
        return float(raw)


def run_leaderboard(settings: LemmaSettings, *, top: int, sort: str) -> None:
    """Print miner-facing leaderboard columns from metagraph."""
    try:
        subtensor = get_subtensor(settings)
    except Exception as e:  # noqa: BLE001
        raise click.ClickException(f"chain RPC: {e}") from e

    netuid = settings.netuid
    mg = subtensor.metagraph(netuid)
    try:
        n = int(mg.n.item())  # type: ignore[union-attr]
    except Exception:
        n = int(mg.n)

    rows: list[tuple[int, float, float, float, str, str]] = []
    for uid in range(n):
        stake = _float_at(mg.S, uid)
        inc = _float_at(mg.I, uid) if hasattr(mg, "I") else 0.0
        tru = _float_at(mg.T, uid) if hasattr(mg, "T") else 0.0
        hk_list = getattr(mg, "hotkeys", [])
        hk = str(hk_list[uid]) if uid < len(hk_list) else ""
        hk_short = (hk[:10] + "…") if len(hk) > 12 else hk
        ip = ""
        axons = getattr(mg, "axons", [])
        if uid < len(axons) and axons[uid] is not None:
            ax = axons[uid]
            try:
                raw_ip = getattr(ax, "ip_str", None)
                if raw_ip:
                    ip = str(raw_ip)
                else:
                    lip = getattr(ax, "ip", None)
                    ip = str(lip() if callable(lip) else (lip or ""))
            except Exception:
                ip = ""
        rows.append((uid, stake, inc, tru, ip, hk_short))

    key = {"stake": 1, "incentive": 2, "trust": 3}.get(sort, 1)
    rows.sort(key=lambda r: -r[key])

    click.echo(
        stylize("Leaderboard  ", fg="cyan", bold=True)
        + stylize(f"netuid={netuid}  n={n}  sort={sort}  (metagraph snapshot)\n", dim=True),
        nl=False,
    )
    click.echo(
        stylize(
            "UID   Stake(ρ)   Incentive   Trust   IP (axon)     Hotkey (short)\n",
            dim=True,
        ),
        nl=False,
    )
    w_uid, w_st, w_inc, w_tr = 3, 10, 9, 7
    for uid, stake, inc, tru, ip, hk in rows[: max(1, min(top, 64))]:
        ip_d = (ip or "—")[: 25]
        click.echo(
            f"{uid:>{w_uid}}  {stake:>{w_st}.4f}  {inc:>{w_inc}.4f}  {tru:>{w_tr}.4f}  "
            f"{ip_d.ljust(25)}  {hk}"
        )
    click.echo(
        stylize(
            "\nThis is chain stake/incentive, not per-challenge Lean proof quality. "
            "A future idea: per-miner “problems passed / judge scores” (UTC day) would need an indexer or "
            "extra exports — not wired here yet.\n"
            "Your own runs: LEMMA_MINER_FORWARD_SUMMARY + optional LEMMA_MINER_LOCAL_VERIFY.\n",
            dim=True,
        ),
        nl=False,
    )
