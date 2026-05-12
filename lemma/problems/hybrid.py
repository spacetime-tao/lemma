"""Deterministic hybrid problem source: generated traffic plus curated breadth."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any

from lemma.catalog.constants import DEFAULT_LEAN_TOOLCHAIN, DEFAULT_MATHLIB_REV
from lemma.problems.base import Problem, ProblemSource
from lemma.problems.generated import (
    GeneratedProblemSource,
    generated_registry_canonical_dict,
    generated_registry_sha256,
)

HYBRID_RNG_MIX_TAG = "lemma_hybrid_problem_rng_v1"
DEFAULT_HYBRID_WEIGHTS: dict[str, int] = {"generated": 60, "catalog": 40}
CURATED_CATALOG_PATH = Path(__file__).resolve().parent / "curated_catalog.json"

_BASE_ROW_KEYS = frozenset(
    {
        "id",
        "theorem_name",
        "type_expr",
        "split",
        "lean_toolchain",
        "mathlib_rev",
        "imports",
    }
)
_REQUIRED_CURATED_KEYS = _BASE_ROW_KEYS | frozenset({"informal_statement", "topic", "family"})


def _mixed_seed(tag: str, seed: int) -> int:
    digest = hashlib.sha256(f"{HYBRID_RNG_MIX_TAG}|{tag}|{int(seed)}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _load_curated_rows(path: Path | None = None) -> list[dict[str, Any]]:
    raw = (path or CURATED_CATALOG_PATH).read_text(encoding="utf-8")
    rows = json.loads(raw)
    if not isinstance(rows, list):
        raise ValueError("curated catalog must be a JSON array")
    return rows


def validate_curated_catalog_rows(rows: list[dict[str, Any]]) -> None:
    """Cheap live-supply gate for dashboard metadata and deterministic catalog rows."""
    errors: list[str] = []
    seen: set[str] = set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"row {i}: expected object")
            continue
        rid = str(row.get("id") or "")
        if not rid:
            errors.append(f"row {i}: missing id")
        elif rid in seen:
            errors.append(f"row {i}: duplicate id {rid!r}")
        seen.add(rid)
        missing = sorted(k for k in _REQUIRED_CURATED_KEYS if not str(row.get(k) or "").strip())
        if missing:
            errors.append(f"row {i} id={rid!r}: missing {', '.join(missing)}")
        if row.get("lean_toolchain") != DEFAULT_LEAN_TOOLCHAIN:
            errors.append(f"row {i} id={rid!r}: lean_toolchain must match {DEFAULT_LEAN_TOOLCHAIN}")
        if row.get("mathlib_rev") != DEFAULT_MATHLIB_REV:
            errors.append(f"row {i} id={rid!r}: mathlib_rev must match {DEFAULT_MATHLIB_REV}")
        if row.get("informal_statement") == "Prove the displayed generated Lean theorem.":
            errors.append(f"row {i} id={rid!r}: informal_statement is fallback text")
    if errors:
        raise ValueError("curated catalog metadata gate failed:\n- " + "\n- ".join(errors))


def curated_catalog_canonical_rows(path: Path | None = None) -> list[dict[str, Any]]:
    rows = _load_curated_rows(path)
    validate_curated_catalog_rows(rows)
    return sorted(rows, key=lambda r: str(r["id"]))


def curated_catalog_sha256(path: Path | None = None) -> str:
    canonical = json.dumps(curated_catalog_canonical_rows(path), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def problem_supply_registry_canonical_dict(
    *,
    generated_weight: int = DEFAULT_HYBRID_WEIGHTS["generated"],
    catalog_weight: int = DEFAULT_HYBRID_WEIGHTS["catalog"],
    curated_catalog_path: Path | None = None,
) -> dict[str, object]:
    rows = curated_catalog_canonical_rows(curated_catalog_path)
    return {
        "kind": "lemma_problem_supply_registry_v1",
        "rng_mix_tag": HYBRID_RNG_MIX_TAG,
        "weights": {"generated": int(generated_weight), "catalog": int(catalog_weight)},
        "generated_registry_sha256": generated_registry_sha256(),
        "generated_registry": generated_registry_canonical_dict(),
        "curated_catalog_sha256": curated_catalog_sha256(curated_catalog_path),
        "curated_count": len(rows),
        "curated_splits": sorted({str(row["split"]) for row in rows}),
        "curated_topics": sorted({str(row["topic"]) for row in rows}),
    }


def problem_supply_registry_sha256(
    *,
    generated_weight: int = DEFAULT_HYBRID_WEIGHTS["generated"],
    catalog_weight: int = DEFAULT_HYBRID_WEIGHTS["catalog"],
    curated_catalog_path: Path | None = None,
) -> str:
    canonical = json.dumps(
        problem_supply_registry_canonical_dict(
            generated_weight=generated_weight,
            catalog_weight=catalog_weight,
            curated_catalog_path=curated_catalog_path,
        ),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class CuratedCatalogSource(ProblemSource):
    """Bundled reviewed theorem pack with authored public statements."""

    def __init__(self, path: Path | None = None) -> None:
        self._rows = curated_catalog_canonical_rows(path)
        self._problems = [_row_to_problem(row) for row in self._rows]

    def all_problems(self) -> list[Problem]:
        return list(self._problems)

    def sample(self, seed: int, split: str | None = None) -> Problem:
        rng = random.Random(_mixed_seed("catalog", seed))
        split_key = (split or "").strip().lower()
        pool = [p for p in self._problems if not split_key or p.split.lower() == split_key]
        if not pool:
            pool = self._problems
        return rng.choice(pool)

    def get(self, problem_id: str) -> Problem:
        for p in self._problems:
            if p.id == problem_id:
                return p
        raise KeyError(problem_id)


class HybridProblemSource(ProblemSource):
    """Deterministic weighted mix of generated and curated theorem supply."""

    def __init__(
        self,
        *,
        generated: GeneratedProblemSource | None = None,
        catalog: CuratedCatalogSource | None = None,
        generated_weight: int = DEFAULT_HYBRID_WEIGHTS["generated"],
        catalog_weight: int = DEFAULT_HYBRID_WEIGHTS["catalog"],
    ) -> None:
        self._generated = generated or GeneratedProblemSource()
        self._catalog = catalog or CuratedCatalogSource()
        self._weights = {"generated": max(0, int(generated_weight)), "catalog": max(0, int(catalog_weight))}
        if sum(self._weights.values()) <= 0:
            raise ValueError("hybrid problem weights must include at least one positive lane")

    def all_problems(self) -> list[Problem]:
        return self._catalog.all_problems()

    def sample(self, seed: int, split: str | None = None) -> Problem:
        rng = random.Random(_mixed_seed("hybrid", seed))
        lane = _pick_lane(rng, self._weights)
        if lane == "generated":
            return _require_public_statement(self._generated.sample(seed, split=split))
        return _require_public_statement(self._catalog.sample(seed, split=split))

    def get(self, problem_id: str) -> Problem:
        if problem_id.startswith("gen/"):
            return _require_public_statement(self._generated.get(problem_id))
        return _require_public_statement(self._catalog.get(problem_id))


def _pick_lane(rng: random.Random, weights: dict[str, int]) -> str:
    pick = rng.randrange(sum(weights.values()))
    return "generated" if pick < weights["generated"] else "catalog"


def _row_to_problem(row: dict[str, Any]) -> Problem:
    raw_imports = row.get("imports", ("Mathlib",))
    imports = (raw_imports,) if isinstance(raw_imports, str) else tuple(raw_imports)
    extra = {k: v for k, v in row.items() if k not in _BASE_ROW_KEYS}
    extra["source_lane"] = "catalog"
    return Problem(
        id=str(row["id"]),
        theorem_name=str(row["theorem_name"]),
        type_expr=str(row["type_expr"]),
        split=str(row["split"]),
        lean_toolchain=str(row["lean_toolchain"]),
        mathlib_rev=str(row["mathlib_rev"]),
        imports=imports,
        extra=extra,
    )


def _require_public_statement(problem: Problem) -> Problem:
    statement = str(problem.extra.get("informal_statement") or "").strip()
    if not statement or statement == "Prove the displayed generated Lean theorem.":
        raise ValueError(f"problem {problem.id} is missing authored informal_statement")
    return problem
