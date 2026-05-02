"""One dry-run epoch (no chain, fake judge, host Lean off)."""

from __future__ import annotations

import asyncio
import os

from lemma.common.config import LemmaSettings
from lemma.problems.minif2f import MiniF2FSource
from lemma.validator import epoch as ep


async def main() -> None:
    os.environ.setdefault("LEMMA_FAKE_JUDGE", "1")
    os.environ.setdefault("LEMMA_USE_DOCKER", "0")
    settings = LemmaSettings()
    source = MiniF2FSource()
    weights = await ep.run_epoch(settings, source, dry_run=True)
    print(weights)


if __name__ == "__main__":
    asyncio.run(main())
