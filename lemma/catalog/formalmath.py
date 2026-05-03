"""Turn FormalMATH Hugging Face rows into Lemma catalog entries."""

from __future__ import annotations

import re
from typing import Any

from lemma.problems.base import SOLUTION_BRIDGE_THEOREM


def _insert_import_submission(code: str, theorem_name: str) -> str:
    lines = code.splitlines()
    insert_at = 0
    while insert_at < len(lines) and lines[insert_at].strip().startswith("import "):
        insert_at += 1
    lines.insert(insert_at, "import Submission")
    text = "\n".join(lines)
    text = re.sub(
        r"(:=\s*by\s*\n)\s*sorry\s*$",
        rf"\1  exact Submission.{theorem_name}",
        text,
        flags=re.MULTILINE,
    )
    if "exact Submission" not in text:
        text = re.sub(
            r":=\s*by\s+sorry\s*$",
            f":= by\n  exact Submission.{theorem_name}",
            text.strip(),
            flags=re.MULTILINE,
        )
    return text


def _submission_stub(code: str, _theorem_name: str) -> str:
    lines = code.splitlines()
    imports = [ln for ln in lines if ln.strip().startswith("import ")]
    rest = [ln for ln in lines if not ln.strip().startswith("import ")]
    inner = "\n".join(rest).strip()
    inner = re.sub(
        r"(:=\s*by\s*\n)\s*sorry\s*$",
        r"\1  sorry",
        inner,
        flags=re.MULTILINE,
    )
    if "sorry" not in inner and ":=" in inner:
        inner = inner.rstrip() + "\n  sorry"
    imps = "\n".join(imports)
    return f"{imps}\n\nnamespace Submission\n\n{inner}\n\nend Submission\n"


def row_from_hf_record(rec: dict[str, Any], idx: int, *, split_tag: str = "formalmath") -> dict[str, Any]:
    code = (rec.get("autoformalization") or "").strip()
    if not code:
        raise ValueError("missing autoformalization")

    if re.search(r":=\s*by\s*$", code):
        code = code + "\n  sorry"
    elif "sorry" not in code and ":=" in code:
        code = code.rstrip() + "\n  sorry"

    m = re.search(r"theorem\s+(\w+)", code)
    if not m:
        raise ValueError("no theorem in autoformalization")
    name = m.group(1)

    solution_full = _insert_import_submission(code, name)
    solution_full = re.sub(
        rf"\btheorem\s+{re.escape(name)}\b",
        f"theorem {SOLUTION_BRIDGE_THEOREM}",
        solution_full,
        count=1,
    )
    submission_stub = _submission_stub(code, name)

    domain = str(rec.get("domain") or "")[:300]
    sid = str(rec.get("theorem_names") or f"row_{idx}")[:120]

    topic = split_tag.replace("formalmath_", "formalmath/", 1)
    return {
        "id": f"{split_tag}/{sid}_{idx}",
        "theorem_name": name,
        "type_expr": domain or "FormalMATH",
        "split": split_tag,
        "topic": topic,
        "imports": [],
        "challenge_full": code,
        "solution_full": solution_full,
        "submission_stub": submission_stub,
        "source_ref": sid,
    }
