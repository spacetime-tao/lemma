"""Render a read-only Lemma ops dashboard from SSH-accessible hosts."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path

DEFAULT_VALIDATOR_HOST = "<validator-ssh-host>"
DEFAULT_MINER_HOST = "<miner-ssh-host>"
DEFAULT_MINER_PORTS = (8091, 8092, 8093, 8094, 8095, 8096)

SERVICE_RE = re.compile(r"^\s*(lemma\S+\.service)\s+\S+\s+(\S+)\s+(\S+)\s+(.+)$")
KEY_VALUE_RE = re.compile(r"(\w+)=([^\s]+)")
MINER_SUMMARY_RE = re.compile(
    r"miner_forward_summary theorem_id=(?P<theorem_id>\S+) split=(?P<split>\S+).*?"
    r"prover_s=(?P<prover_s>[0-9.]+)s proof_chars=(?P<proof_chars>\d+).*?"
    r"session_forwards=(?P<session_forwards>\d+) session_avg_prover_s=(?P<session_avg>[0-9.]+)s "
    r"session_local_ok=(?P<local_ok>\d+) session_local_fail=(?P<local_fail>\d+)"
)
MINER_LISTEN_RE = re.compile(r"Miner axon listening netuid=(?P<netuid>\d+) port=(?P<port>\d+) hotkey=(?P<hotkey>\S+)")
EPOCH_RE = re.compile(r"lemma_epoch_summary (?P<body>.+?)\s+\[")
SET_WEIGHTS_RE = re.compile(r"set_weights success=(?P<success>\S+) message=(?P<message>.*)$")


@dataclass(frozen=True)
class CommandResult:
    label: str
    ok: bool
    output: str


@dataclass(frozen=True)
class ServiceRow:
    name: str
    active: str
    sub: str
    description: str


@dataclass(frozen=True)
class PortRow:
    host: str
    port: int
    open: bool
    error: str


def main() -> None:
    args = _parser().parse_args()
    validator_host = _safe_host(args.validator_host)
    miner_host = _safe_host(args.miner_host)
    miner_ports = tuple(int(p) for p in args.miner_ports.split(",") if p.strip())

    validator = _collect_host("validator", validator_host, args.lines, args.timeout)
    miner = _collect_host("miner", miner_host, args.lines, args.timeout)
    ports = [_probe_port(_address_only(miner_host), port, args.port_timeout) for port in miner_ports]
    worker_health = _ssh(
        validator_host,
        "curl -fsS http://127.0.0.1:8787/health 2>/dev/null || true",
        label="lean worker health",
        timeout=args.timeout,
    )

    html_text = _render_html(
        validator_host=validator_host,
        miner_host=miner_host,
        validator=validator,
        miner=miner,
        ports=ports,
        worker_health=worker_health.output.strip(),
    )
    out = Path(args.out)
    out.write_text(html_text, encoding="utf-8")
    print(f"wrote {out}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validator-host", default=DEFAULT_VALIDATOR_HOST)
    parser.add_argument("--miner-host", default=DEFAULT_MINER_HOST)
    parser.add_argument("--miner-ports", default=",".join(str(p) for p in DEFAULT_MINER_PORTS))
    parser.add_argument("--lines", type=int, default=240, help="Recent log lines to inspect per host.")
    parser.add_argument("--timeout", type=int, default=12, help="SSH command timeout in seconds.")
    parser.add_argument("--port-timeout", type=float, default=2.0, help="TCP probe timeout in seconds.")
    parser.add_argument("--out", default="ops-dashboard.html")
    return parser


def _safe_host(host: str) -> str:
    host = host.strip()
    if not host or host.startswith("-") or any(c.isspace() for c in host):
        raise SystemExit(f"unsafe SSH host: {host!r}")
    return host


def _address_only(host: str) -> str:
    return host.rsplit("@", 1)[-1]


def _ssh(host: str, command: str, *, label: str, timeout: int) -> CommandResult:
    proc = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=8",
            host,
            command,
        ],
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    output = (proc.stdout + proc.stderr).strip()
    return CommandResult(label=label, ok=proc.returncode == 0, output=output)


def _collect_host(role: str, host: str, lines: int, timeout: int) -> dict[str, CommandResult]:
    env_cmd = (
        "for f in /opt/lemma/.env /opt/lemma/.env.miner*; do "
        "[ -f \"$f\" ] || continue; echo \"### $f\"; "
        "grep -E '^(SUBTENSOR_NETWORK|NETUID|BT_WALLET_COLD|BT_WALLET_HOT|BT_VALIDATOR_WALLET_COLD|"
        "BT_VALIDATOR_WALLET_HOT|AXON_EXTERNAL_IP|AXON_PORT|LEAN_SANDBOX_IMAGE|"
        "LEMMA_LEAN_DOCKER_WORKER|LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR)=' \"$f\" || true; "
        "done"
    )
    log_cmd = (
        f"journalctl -b -u 'lemma*' -n {int(lines)} --no-pager 2>/dev/null; "
        f"tail -n {int(lines)} /var/log/lemma-*.log 2>/dev/null || true"
    )
    return {
        "services": _ssh(
            host,
            "systemctl list-units 'lemma*' --type=service --all --no-pager",
            label="services",
            timeout=timeout,
        ),
        "sha": _ssh(host, "git -C /opt/lemma rev-parse --short HEAD", label="git sha", timeout=timeout),
        "env": _ssh(host, env_cmd, label="safe env", timeout=timeout),
        "docker": _ssh(
            host,
            "docker ps --format '{{.Names}}\t{{.Status}}\t{{.Image}}' 2>/dev/null || true",
            label="docker",
            timeout=timeout,
        ),
        "logs": _ssh(host, log_cmd, label=f"{role} logs", timeout=timeout),
    }


def _probe_port(host: str, port: int, timeout: float) -> PortRow:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return PortRow(host=host, port=port, open=True, error="")
    except OSError as exc:
        return PortRow(host=host, port=port, open=False, error=str(exc))


def _parse_services(text: str) -> list[ServiceRow]:
    rows: list[ServiceRow] = []
    for line in text.splitlines():
        m = SERVICE_RE.match(line)
        if m:
            rows.append(ServiceRow(name=m.group(1), active=m.group(2), sub=m.group(3), description=m.group(4)))
    return rows


def _parse_latest_epoch(text: str) -> dict[str, str]:
    latest: dict[str, str] = {}
    for line in text.splitlines():
        m = EPOCH_RE.search(line)
        if not m:
            continue
        latest = dict(KEY_VALUE_RE.findall(m.group("body")))
    return latest


def _parse_latest_set_weights(text: str) -> dict[str, str]:
    latest: dict[str, str] = {}
    for line in text.splitlines():
        m = SET_WEIGHTS_RE.search(line)
        if m:
            latest = {"success": m.group("success"), "message": m.group("message")}
    return latest


def _parse_miner_summaries(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        m = MINER_SUMMARY_RE.search(line)
        if m:
            rows.append(m.groupdict())
    return rows[-12:]


def _parse_listeners(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        m = MINER_LISTEN_RE.search(line)
        if m:
            rows.append(m.groupdict())
    return rows[-12:]


def _render_html(
    *,
    validator_host: str,
    miner_host: str,
    validator: dict[str, CommandResult],
    miner: dict[str, CommandResult],
    ports: list[PortRow],
    worker_health: str,
) -> str:
    validator_services = _parse_services(validator["services"].output)
    miner_services = _parse_services(miner["services"].output)
    epoch = _parse_latest_epoch(validator["logs"].output)
    weights = _parse_latest_set_weights(validator["logs"].output)
    summaries = _parse_miner_summaries(miner["logs"].output)
    listeners = _parse_listeners(miner["logs"].output)
    port_open = sum(1 for p in ports if p.open)
    now = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    summary_columns = [
        "theorem_id",
        "split",
        "prover_s",
        "proof_chars",
        "session_forwards",
        "session_avg",
        "local_ok",
        "local_fail",
    ]
    lean_worker = {
        "health": worker_health or "no response",
        "docker": validator["docker"].output or "no running containers reported",
    }

    body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Lemma Ops Dashboard</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f7f4;
      --ink: #1f2528;
      --muted: #5f686d;
      --line: #d9ddd8;
      --panel: #ffffff;
      --ok: #176c43;
      --bad: #a23232;
      --warn: #946200;
      --accent: #275f8f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font: 14px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
    }}
    header {{ padding: 24px 28px 12px; border-bottom: 1px solid var(--line); background: #fff; }}
    main {{ padding: 20px 28px 36px; max-width: 1280px; margin: 0 auto; }}
    h1 {{ margin: 0 0 6px; font-size: 28px; }}
    h2 {{ margin: 24px 0 10px; font-size: 18px; }}
    .muted {{ color: var(--muted); }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; }}
    .metric {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      min-height: 92px;
    }}
    .label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
    .value {{ font-size: 24px; font-weight: 700; margin-top: 8px; }}
    table {{ width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--line); }}
    th, td {{ text-align: left; padding: 9px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }}
    th {{
      font-size: 12px;
      color: var(--muted);
      background: #f1f3f0;
      text-transform: uppercase;
      letter-spacing: .04em;
    }}
    code, pre {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      max-height: 340px;
      overflow: auto;
      background: #111820;
      color: #e6edf3;
      padding: 12px;
      border-radius: 8px;
    }}
    .ok {{ color: var(--ok); font-weight: 700; }}
    .bad {{ color: var(--bad); font-weight: 700; }}
    .warn {{ color: var(--warn); font-weight: 700; }}
    .note {{ background: #fff8df; border: 1px solid #ead892; border-radius: 8px; padding: 12px; color: #4c3b00; }}
  </style>
</head>
<body>
  <header>
    <h1>Lemma Ops Dashboard</h1>
    <div class="muted">
      Collected {html.escape(now)} from {html.escape(validator_host)} and {html.escape(miner_host)}.
    </div>
  </header>
  <main>
    <section class="grid">
      {_metric("Validator Services", _active_count(validator_services))}
      {_metric("Miner Services", _active_count(miner_services))}
      {_metric("Miner Ports Open", f"{port_open}/{len(ports)}")}
      {_metric("Latest Scored", epoch.get("scored", "?"))}
      {_metric("Latest Verified", epoch.get("verified", "?"))}
      {_metric("Set Weights", weights.get("success", "?"))}
    </section>
    <h2>Plain English Read</h2>
    <div class="note">
      This page is read-only. It shows whether services are alive, ports are reachable,
      miners are answering, and the validator has recently scored and set weights.
      It does not change rewards, and miner logs alone cannot prove a submitted proof passed.
      Validator logs are the source for verified/scored counts.
    </div>
    <h2>Services</h2>
    {_services_table("Validator / Lean worker", validator_services)}
    {_services_table("Miners", miner_services)}
    <h2>Miner Ports</h2>
    {_ports_table(ports)}
    <h2>Latest Validator Round</h2>
    {_kv_table(epoch or {"status": "no lemma_epoch_summary found in sampled logs"})}
    <h2>Latest Miner Summaries</h2>
    {_dict_table(summaries, summary_columns)}
    <h2>Miner Listeners</h2>
    {_dict_table(listeners, ["netuid", "port", "hotkey"])}
    <h2>Lean Worker</h2>
    {_kv_table(lean_worker)}
    <h2>Safe Env Snapshot</h2>
    <pre>{html.escape(validator["env"].output + chr(10) + chr(10) + miner["env"].output)}</pre>
    <h2>Recent Validator Logs</h2>
    <pre>{html.escape(validator["logs"].output[-12000:])}</pre>
    <h2>Recent Miner Logs</h2>
    <pre>{html.escape(miner["logs"].output[-12000:])}</pre>
  </main>
</body>
</html>
"""
    return body


def _active_count(rows: list[ServiceRow]) -> str:
    active = sum(1 for row in rows if row.active == "active" and row.sub == "running")
    return f"{active}/{len(rows)}"


def _metric(label: str, value: str) -> str:
    return (
        '<div class="metric">'
        f'<div class="label">{html.escape(label)}</div>'
        f'<div class="value">{html.escape(value)}</div>'
        "</div>"
    )


def _services_table(title: str, rows: list[ServiceRow]) -> str:
    data = "".join(
        "<tr>"
        f"<td><code>{html.escape(row.name)}</code></td>"
        f"<td>{_status(row.active == 'active' and row.sub == 'running', row.active + '/' + row.sub)}</td>"
        f"<td>{html.escape(row.description)}</td>"
        "</tr>"
        for row in rows
    )
    return (
        f"<h3>{html.escape(title)}</h3>"
        "<table><tr><th>service</th><th>state</th><th>description</th></tr>"
        f"{data}</table>"
    )


def _ports_table(rows: list[PortRow]) -> str:
    data = "".join(
        "<tr>"
        f"<td><code>{html.escape(row.host)}:{row.port}</code></td>"
        f"<td>{_status(row.open, 'open' if row.open else 'closed')}</td>"
        f"<td>{html.escape(row.error)}</td>"
        "</tr>"
        for row in rows
    )
    return f"<table><tr><th>address</th><th>state</th><th>detail</th></tr>{data}</table>"


def _kv_table(values: dict[str, str]) -> str:
    data = "".join(
        f"<tr><td><code>{html.escape(k)}</code></td><td>{html.escape(v)}</td></tr>"
        for k, v in values.items()
    )
    return f"<table><tr><th>key</th><th>value</th></tr>{data}</table>"


def _dict_table(rows: list[dict[str, str]], columns: list[str]) -> str:
    if not rows:
        return '<div class="muted">No matching rows found in sampled logs.</div>'
    head = "".join(f"<th>{html.escape(col)}</th>" for col in columns)
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(row.get(col, ''))}</td>" for col in columns) + "</tr>"
        for row in rows
    )
    return f"<table><tr>{head}</tr>{body}</table>"


def _status(ok: bool, text: str) -> str:
    cls = "ok" if ok else "bad"
    return f'<span class="{cls}">{html.escape(text)}</span>'


if __name__ == "__main__":
    main()
