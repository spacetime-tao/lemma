"""Render a sanitized public Lemma dashboard."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lemma.problems.generated import GENERATED_FAMILY_STATEMENTS

SECONDS_PER_HOUR = 3600.0

PUBLIC_DASHBOARD_SCHEMA_VERSION = 4
FORALL_RE = re.compile(r"^(?:forall|∀)\s+(.+?)\s+:\s+(.+?),\s+(.+)$")
TOPIC_LABELS = {
    "nat": "natural-number arithmetic",
    "prop": "propositional logic",
    "real_basic": "real-number analysis",
    "finite_sets": "finite set theory",
    "matrix_light": "linear algebra",
    "metric_light": "metric topology",
    "mod_arith": "modular arithmetic",
}


@dataclass(frozen=True)
class PublicTheorem:
    label: str
    seed: int
    theorem_id: str
    name: str
    split: str
    topic: str
    source_lane: str
    type_expr: str
    plain_english: str
    explanation: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "seed": self.seed,
            "theorem_id": self.theorem_id,
            "name": self.name,
            "split": self.split,
            "topic": self.topic,
            "source_lane": self.source_lane,
            "type_expr": self.type_expr,
            "plain_english": self.plain_english,
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class PublicMiner:
    uid: int
    coldkey: str
    hotkey: str
    score: float | None
    validator_rolling_score: float | None
    correct_theorems_24h: int
    passed_prior_round: bool | None = None
    uid_url: str = ""
    coldkey_url: str = ""
    hotkey_url: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "uid": self.uid,
            "coldkey": self.coldkey,
            "hotkey": self.hotkey,
            "score": self.score,
            "validator_rolling_score": self.validator_rolling_score,
            "correct_theorems_24h": self.correct_theorems_24h,
            "passed_prior_round": self.passed_prior_round,
            "uid_url": self.uid_url,
            "coldkey_url": self.coldkey_url,
            "hotkey_url": self.hotkey_url,
        }


@dataclass(frozen=True)
class LatestRoundProofs:
    count: int | None
    passed_uids: frozenset[int] | None
    rolling_score_by_uid: dict[int, float] | None = None


def main() -> None:
    args = _parser().parse_args()

    from lemma.common.config import LemmaSettings
    from lemma.common.problem_seed import effective_chain_head_for_problem_seed, resolve_problem_seed
    from lemma.common.subtensor import get_subtensor
    from lemma.problems.factory import get_problem_source

    settings = LemmaSettings()
    subtensor = get_subtensor(settings)
    chain_head = int(args.chain_head) if args.chain_head is not None else int(subtensor.get_current_block())
    seed_head = effective_chain_head_for_problem_seed(
        chain_head,
        int(settings.lemma_problem_seed_chain_head_slack_blocks or 0),
    )
    problem_seed, seed_tag = resolve_problem_seed(
        chain_head_block=seed_head,
        netuid=settings.netuid,
        mode=settings.problem_seed_mode,
        quantize_blocks=settings.problem_seed_quantize_blocks,
        subtensor=subtensor,
    )
    theorems = build_theorem_triplet(
        problem_seed=problem_seed,
        seed_tag=seed_tag,
        mode=settings.problem_seed_mode,
        quantize_blocks=settings.problem_seed_quantize_blocks,
        problem_source=get_problem_source(settings),
    )
    export_path = Path(args.summary_jsonl) if args.summary_jsonl else settings.training_export_jsonl
    min_summary_block = lookback_min_block(
        current_block=chain_head,
        seconds_per_block=float(settings.block_time_sec_estimate),
        hours=float(args.lookback_hours),
    )
    correct_counts = correct_theorem_counts(
        export_path,
        current_block=chain_head,
        seconds_per_block=float(settings.block_time_sec_estimate),
        hours=float(args.lookback_hours),
    )
    latest_round = latest_round_proofs(export_path, min_block=min_summary_block)
    miners = public_miner_rows(
        subtensor.metagraph(settings.netuid),
        correct_counts,
        passed_prior_round_uids=latest_round.passed_uids,
        rolling_score_by_uid=latest_round.rolling_score_by_uid,
        network=settings.subtensor_network,
        netuid=settings.netuid,
        uid_url_template=args.uid_url_template,
        account_url_template=args.account_url_template,
    )
    generated_at = dt.datetime.now(dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    variant_metadata = theorem_variant_metadata(bool(settings.lemma_uid_variant_problems))
    payload = {
        "schema_version": PUBLIC_DASHBOARD_SCHEMA_VERSION,
        **variant_metadata,
        "generated_at": generated_at,
        "network": settings.subtensor_network,
        "netuid": settings.netuid,
        "chain_head_block": chain_head,
        "problem_seed_chain_head": seed_head,
        "problem_seed": problem_seed,
        "problem_seed_mode": settings.problem_seed_mode,
        "problem_seed_quantize_blocks": settings.problem_seed_quantize_blocks,
        "block_time_sec_estimate": float(settings.block_time_sec_estimate),
        "problem_seed_tag": seed_tag,
        "score_source": "metagraph_incentive",
        "validator_score_source": "difficulty_weighted_rolling_validator_score",
        "correct_count_window_hours": float(args.lookback_hours),
        "proofs_passed_prior_round": latest_round.count,
        "theorems": {t.label: t.as_dict() for t in theorems},
        "miners": [m.as_dict() for m in miners],
    }

    json_out = Path(args.json_out)
    json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.html_out:
        html_out = Path(args.html_out)
        html_out.write_text(render_public_html(payload), encoding="utf-8")
        print(f"wrote {json_out} and {html_out}")
    else:
        print(f"wrote {json_out}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-jsonl", help="Validator summary/full JSONL to aggregate for 24h counts.")
    parser.add_argument("--lookback-hours", type=float, default=24.0)
    parser.add_argument("--chain-head", type=int, help="Override chain head, mostly for reproducible snapshots.")
    parser.add_argument("--json-out", default="public-dashboard.json")
    parser.add_argument("--html-out", default="public-dashboard.html")
    parser.add_argument("--uid-url-template", default="", help="Optional URL template with {uid}, {netuid}, {network}.")
    parser.add_argument(
        "--account-url-template",
        default="",
        help="Optional URL template with {address}, {netuid}, {network} for coldkeys and hotkeys.",
    )
    return parser


def build_theorem_triplet(
    *,
    problem_seed: int,
    seed_tag: str,
    mode: str,
    quantize_blocks: int,
    problem_source: Any,
) -> list[PublicTheorem]:
    step = 1 if mode == "subnet_epoch" and seed_tag == "subnet_epoch" else max(1, int(quantize_blocks))
    seeds = {
        "previous": max(0, int(problem_seed) - step),
        "current": int(problem_seed),
        "next": int(problem_seed) + step,
    }
    return [_public_theorem(label, seed, problem_source.sample(seed=seed)) for label, seed in seeds.items()]


def theorem_variant_metadata(uid_variant_problems: bool) -> dict[str, bool | str]:
    return {
        "uid_variant_problems": bool(uid_variant_problems),
        "theorem_display_mode": "uid_variants" if uid_variant_problems else "shared",
    }


def _public_theorem(label: str, seed: int, problem: Any) -> PublicTheorem:
    extra = getattr(problem, "extra", {}) if isinstance(getattr(problem, "extra", {}), dict) else {}
    split = str(getattr(problem, "split", ""))
    topic = str(extra.get("topic") or "")
    source_lane = str(extra.get("source_lane") or "")
    type_expr = str(getattr(problem, "type_expr", ""))
    plain_english = public_statement_for_problem(problem)
    return PublicTheorem(
        label=label,
        seed=int(seed),
        theorem_id=str(getattr(problem, "id", "")),
        name=str(getattr(problem, "theorem_name", "")),
        split=split,
        topic=topic,
        source_lane=source_lane,
        type_expr=type_expr,
        plain_english=plain_english,
        explanation=plain_english,
    )


def public_statement_for_problem(problem: Any) -> str:
    extra = getattr(problem, "extra", {}) if isinstance(getattr(problem, "extra", {}), dict) else {}
    authored = str(extra.get("informal_statement") or "").strip()
    if authored:
        return authored
    family = str(extra.get("family") or "")
    if family:
        return GENERATED_FAMILY_STATEMENTS.get(family, "Prove the displayed generated Lean theorem.")
    return explain_theorem(type_expr=str(getattr(problem, "type_expr", "")))


def explain_theorem(*, type_expr: str, split: str = "", topic: str = "") -> str:
    """Compatibility name for the public plain-English theorem text."""
    plain = englishish_lean(type_expr)
    return f"Prove that {plain}."


def human_topic(topic: str) -> str:
    raw = (topic or "generated theorem").strip()
    if not raw:
        return "generated theorem"
    parts = [p for p in raw.split(".") if p]
    key = re.sub(r"_(?:light|lite)$", "", parts[-1] if parts else raw, flags=re.IGNORECASE)
    if key in TOPIC_LABELS:
        return TOPIC_LABELS[key]
    return key.replace("_", " ") if key else raw


def englishish_lean(type_expr: str) -> str:
    stripped = type_expr.strip()
    if m := FORALL_RE.match(stripped):
        variables = " and ".join(m.group(1).split())
        noun = _lean_type_noun(m.group(2))
        return f"for every {noun} {variables}, {englishish_lean(m.group(3))}"

    text = f" {stripped} "
    replacements = (
        ("forall ", "for every "),
        (" : Nat", " is a natural number"),
        (" : Int", " is an integer"),
        (" : Real", " is a real number"),
        (" : Prop", " is a proposition"),
        (" : Type", " is a type"),
        (" -> ", " implies "),
        (" \u2192 ", " implies "),
        (" \u2227 ", " and "),
        (" \u2228 ", " or "),
        (" \u2264 ", " is at most "),
        (" \u2265 ", " is at least "),
        (" < ", " is less than "),
        (" > ", " is greater than "),
        (" = ", " equals "),
        (" + ", " plus "),
        (" * ", " times "),
        (" ^ ", " to the power "),
        (" \u2208 ", " is in "),
        (" \u2286 ", " is a subset of "),
        ("\u00ac", "not "),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return " ".join(text.replace(",", ", ").split())


def _lean_type_noun(type_name: str) -> str:
    return {
        "Nat": "natural number",
        "Set Nat": "set of natural numbers",
        "Finset Nat": "finite set of natural numbers",
        "List Nat": "list of natural numbers",
        "Int": "integer",
        "ℤ": "integer",
        "Real": "real number",
        "ℝ": "real number",
        "Prop": "proposition",
        "Type": "type",
    }.get(type_name, type_name)


def correct_theorem_counts(
    path: Path | None,
    *,
    current_block: int,
    seconds_per_block: float,
    hours: float,
) -> dict[int, int]:
    if path is None or not path.exists():
        return {}
    min_block = lookback_min_block(
        current_block=current_block,
        seconds_per_block=seconds_per_block,
        hours=hours,
    )
    seen: dict[int, set[str]] = defaultdict(set)
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        uid = _as_int(obj.get("uid"))
        block = _as_int(obj.get("block"))
        theorem_id = str(obj.get("theorem_id") or "")
        if uid is None or block is None or block < min_block or not theorem_id:
            continue
        seen[uid].add(theorem_id)
    return {uid: len(theorem_ids) for uid, theorem_ids in seen.items()}


def lookback_min_block(*, current_block: int, seconds_per_block: float, hours: float) -> int:
    lookback_blocks = int(max(1.0, hours * SECONDS_PER_HOUR / max(1.0, seconds_per_block)))
    return int(current_block) - lookback_blocks


def latest_round_proofs(path: Path | None, *, min_block: int | None = None) -> LatestRoundProofs:
    if path is None or not path.exists():
        return LatestRoundProofs(None, None)
    latest_key: tuple[int, str] | None = None
    by_round: dict[tuple[int, str], set[int]] = defaultdict(set)
    rolling_by_round: dict[tuple[int, str], dict[int, float]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        block = _as_int(obj.get("block"))
        theorem_id = str(obj.get("theorem_id") or "")
        if block is None or not theorem_id:
            continue
        if min_block is not None and block < min_block:
            continue
        key = (block, theorem_id)
        if obj.get("record_type") == "round_summary":
            by_round[key].update(
                uid
                for uid in (_as_int(raw) for raw in obj.get("passed_uids", []))
                if uid is not None
            )
            rolling_by_round[key] = _uid_float_map(obj.get("rolling_score_by_uid"))
        else:
            uid = _as_int(obj.get("uid"))
            if uid is None:
                continue
            by_round[key].add(uid)
        if latest_key is None or key > latest_key:
            latest_key = key
    if latest_key is None:
        return LatestRoundProofs(None, None)
    passed_uids = frozenset(by_round[latest_key])
    return LatestRoundProofs(len(passed_uids), passed_uids, rolling_by_round.get(latest_key))


def latest_round_proof_count(path: Path | None) -> int | None:
    return latest_round_proofs(path).count


def public_miner_rows(
    metagraph: Any,
    correct_counts: dict[int, int],
    *,
    passed_prior_round_uids: frozenset[int] | set[int] | None = None,
    rolling_score_by_uid: dict[int, float] | None = None,
    network: str = "",
    netuid: int = 0,
    uid_url_template: str = "",
    account_url_template: str = "",
) -> list[PublicMiner]:
    n = _as_int(getattr(metagraph, "n", 0)) or 0
    rows: list[PublicMiner] = []
    score_values = _first_attr(metagraph, ("I", "incentive", "incentives"))
    rolling_scores = rolling_score_by_uid or {}
    for uid in range(n):
        coldkey = str(_sequence_value(getattr(metagraph, "coldkeys", ()), uid) or "")
        hotkey = str(_sequence_value(getattr(metagraph, "hotkeys", ()), uid) or "")
        rows.append(
            PublicMiner(
                uid=uid,
                coldkey=coldkey,
                hotkey=hotkey,
                score=_as_float(_sequence_value(score_values, uid)),
                validator_rolling_score=_as_float(rolling_scores.get(uid)),
                correct_theorems_24h=correct_counts.get(uid, 0),
                passed_prior_round=None if passed_prior_round_uids is None else uid in passed_prior_round_uids,
                uid_url=_format_url(uid_url_template, uid=uid, netuid=netuid, network=network),
                coldkey_url=_format_url(account_url_template, address=coldkey, netuid=netuid, network=network),
                hotkey_url=_format_url(account_url_template, address=hotkey, netuid=netuid, network=network),
            ),
        )
    return sorted(rows, key=lambda r: (-(r.validator_rolling_score or 0.0), -(r.score or 0.0), r.uid))


def render_public_html(payload: dict[str, Any]) -> str:
    theorems = payload.get("theorems") or {}
    miners = payload.get("miners") or []
    generated_at = _esc(str(payload.get("generated_at") or ""))
    score_source = _esc(str(payload.get("score_source") or ""))
    validator_score_source = _esc(str(payload.get("validator_score_source") or ""))
    rows = "\n".join(_miner_row(m) for m in miners) or '<tr><td colspan="7">No miners found.</td></tr>'
    rubric = _rubric_html()
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Lemma Public Dashboard</title>
  <style>
    :root {{
      --bg: #f6f7f5;
      --ink: #182024;
      --muted: #5c666b;
      --line: #d8ddd8;
      --panel: #ffffff;
      --accent: #176c43;
      --soft: #eef1ee;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 40px;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-end;
      margin-bottom: 18px;
    }}
    h1, h2, h3, p {{ margin: 0; }}
    h1 {{ font-size: 28px; }}
    h2 {{ font-size: 18px; margin: 24px 0 10px; }}
    h3 {{ font-size: 16px; }}
    .meta {{ color: var(--muted); text-align: right; }}
    .grid-3 {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }}
    .current {{ border-color: var(--accent); }}
    .muted {{ color: var(--muted); }}
    .label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .06em;
    }}
    .explain {{ margin-top: 10px; color: var(--muted); }}
    .goal {{
      margin-top: 10px;
      padding: 10px;
      background: var(--soft);
      border-radius: 6px;
      overflow-wrap: anywhere;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
    }}
    .rubric {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }}
    .rubric dl {{
      display: grid;
      grid-template-columns: max-content 1fr;
      gap: 8px 12px;
      margin: 10px 0 0;
    }}
    .rubric dt {{ font-weight: 700; }}
    .rubric dd {{ margin: 0; color: var(--muted); }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid var(--line);
    }}
    th, td {{
      padding: 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    th {{ font-size: 12px; color: var(--muted); }}
    th button {{
      border: 0;
      padding: 0;
      background: transparent;
      color: inherit;
      cursor: pointer;
      font: inherit;
      font-weight: 700;
    }}
    th button::after {{
      content: " \\2195";
      color: var(--muted);
      font-weight: 400;
    }}
    a {{ color: #0b5f86; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .addr {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      overflow-wrap: anywhere;
      font-size: 12px;
    }}
    @media (max-width: 820px) {{
      header {{ display: block; }}
      .meta {{ margin-top: 8px; text-align: left; }}
      .grid-3, .rubric {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Lemma Public Dashboard</h1>
        <p>Public theorem schedule, validator rolling scores, and chain incentives.</p>
      </div>
      <p class="meta">Updated {generated_at}<br>Validator score: {validator_score_source}<br>
      Chain score: {score_source}</p>
    </header>

    <section class="grid-3">
      {_theorem_card(theorems.get("previous"), "previous")}
      {_theorem_card(theorems.get("current"), "current")}
      {_theorem_card(theorems.get("next"), "next")}
    </section>

    <h2>Problem Rubric</h2>
    {rubric}

    <h2>Miners</h2>
    <p class="muted">
      UIDs, coldkeys, and hotkeys can be rendered as explorer links when a mainnet explorer URL template is configured.
    </p>
    <table id="miners-table">
      <thead>
        <tr>
          <th><button type="button" data-sort="number">UID</button></th>
          <th><button type="button" data-sort="text">Coldkey</button></th>
          <th><button type="button" data-sort="text">Hotkey</button></th>
          <th><button type="button" data-sort="number">Validator Rolling Score</button></th>
          <th><button type="button" data-sort="number">Chain Score</button></th>
          <th><button type="button" data-sort="number">Passed Previous Round</button></th>
          <th><button type="button" data-sort="number">Correct Theorems 24h</button></th>
        </tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>
  </main>
  <script>
    const table = document.getElementById("miners-table");
    const tbody = table.querySelector("tbody");
    const directions = new Map();
    table.querySelectorAll("th button").forEach((button, column) => {{
      button.addEventListener("click", () => {{
        const dir = directions.get(column) === "asc" ? "desc" : "asc";
        directions.set(column, dir);
        const numeric = button.dataset.sort === "number";
        const rows = Array.from(tbody.querySelectorAll("tr"));
        rows.sort((a, b) => {{
          const av = a.children[column].dataset.value || a.children[column].textContent.trim();
          const bv = b.children[column].dataset.value || b.children[column].textContent.trim();
          const cmp = numeric ? Number(av) - Number(bv) : av.localeCompare(bv);
          return dir === "asc" ? cmp : -cmp;
        }});
        rows.forEach((row) => tbody.appendChild(row));
      }});
    }});
  </script>
</body>
</html>
"""


def _theorem_card(obj: Any, label: str) -> str:
    if not isinstance(obj, dict):
        return f'<article class="panel"><p class="label">{_esc(label)}</p><h3>Unknown</h3></article>'
    current_cls = " current" if label == "current" else ""
    statement = str(obj.get("plain_english") or obj.get("explanation") or "Generated Lean theorem.")
    topic = human_topic(str(obj.get("topic") or ""))
    lane = str(obj.get("source_lane") or "")
    meta = " - ".join(part for part in (str(obj.get("split") or ""), topic, lane) if part)
    return f"""<article class="panel{current_cls}">
        <p class="label">{_esc(label)}</p>
        <h3>{_esc(statement)}</h3>
        <p>{_esc(str(obj.get("name") or ""))} - {_esc(meta)}</p>
        <p class="label">Formal theorem to prove</p>
        <div class="goal">{_esc(str(obj.get("type_expr") or ""))}</div>
        <p class="explain">{_esc(str(obj.get("theorem_id") or ""))}</p>
      </article>"""


def _miner_row(obj: Any) -> str:
    if not isinstance(obj, dict):
        return ""
    score = obj.get("score")
    score_text = "?" if score is None else f"{float(score):.6f}"
    rolling = obj.get("validator_rolling_score")
    rolling_text = "?" if rolling is None else f"{float(rolling):.6f}"
    rolling_value = "" if rolling is None else str(float(rolling))
    uid = int(obj.get("uid") or 0)
    score_value = "" if score is None else str(float(score))
    correct = int(obj.get("correct_theorems_24h") or 0)
    passed = obj.get("passed_prior_round")
    passed_value = "" if passed is None else ("1" if passed else "0")
    passed_text = "?" if passed is None else ("&#10003;" if passed else "&times;")
    coldkey = str(obj.get("coldkey") or "")
    hotkey = str(obj.get("hotkey") or "")
    coldkey_link = _link_or_text(coldkey, str(obj.get("coldkey_url") or ""))
    hotkey_link = _link_or_text(hotkey, str(obj.get("hotkey_url") or ""))
    return f"""<tr>
          <td data-value="{uid}">{_link_or_text(str(uid), str(obj.get("uid_url") or ""))}</td>
          <td class="addr" data-value="{_esc(coldkey)}">{coldkey_link}</td>
          <td class="addr" data-value="{_esc(hotkey)}">{hotkey_link}</td>
          <td data-value="{_esc(rolling_value)}">{_esc(rolling_text)}</td>
          <td data-value="{_esc(score_value)}">{_esc(score_text)}</td>
          <td data-value="{_esc(passed_value)}">{passed_text}</td>
          <td data-value="{correct}">{correct}</td>
        </tr>"""


def _rubric_html() -> str:
    return """<section class="rubric">
      <article class="panel">
        <h3>Difficulty</h3>
        <dl>
          <dt>Easy</dt><dd>Short identities and direct facts.</dd>
          <dt>Medium</dt><dd>Common algebra, logic, list, set, and finset lemmas.</dd>
          <dt>Hard</dt><dd>Statements that usually need more structure or imported Mathlib facts.</dd>
        </dl>
      </article>
      <article class="panel">
        <h3>Problem Types</h3>
        <dl>
          <dt>Arithmetic</dt><dd>Natural numbers, integers, reals, powers, divisibility.</dd>
          <dt>Logic</dt><dd>Implications, conjunctions, quantifiers, propositions.</dd>
          <dt>Structures</dt><dd>Lists, sets, finsets, topology, metrics, and linear algebra.</dd>
        </dl>
      </article>
    </section>"""


def _link_or_text(text: str, url: str) -> str:
    label = _esc(text)
    if not url:
        return label
    return f'<a href="{_esc(url)}" rel="noopener noreferrer">{label}</a>'


def _format_url(template: str, **values: object) -> str:
    template = template.strip()
    if not template:
        return ""
    try:
        return template.format(**values)
    except (KeyError, IndexError, ValueError):
        return ""


def _first_attr(obj: Any, names: tuple[str, ...]) -> Any:
    for name in names:
        value = getattr(obj, name, None)
        if value is not None:
            return value
    return None


def _sequence_value(values: Any, index: int) -> Any:
    if values is None:
        return None
    try:
        value = values[index]
    except (IndexError, KeyError, TypeError):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _as_int(value: Any) -> int | None:
    if hasattr(value, "item"):
        value = value.item()
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if hasattr(value, "item"):
        value = value.item()
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _uid_float_map(value: Any) -> dict[int, float]:
    if not isinstance(value, dict):
        return {}
    out: dict[int, float] = {}
    for raw_uid, raw_score in value.items():
        uid = _as_int(raw_uid)
        score = _as_float(raw_score)
        if uid is not None and score is not None:
            out[uid] = score
    return out


def _esc(value: str) -> str:
    return html.escape(value, quote=True)


if __name__ == "__main__":
    main()
