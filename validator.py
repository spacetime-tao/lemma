"""Do not use this file as the Lemma validator.

The historical ``validator.py`` in many subnet templates **only sets weights on UID 0**
(burn / demo). **Lemma scoring** lives in ``lemma/validator/`` and is run via:

    uv run lemma validator start

The old script was moved to ``examples/legacy_subnet_burn_validator.py`` for reference only.
"""

from __future__ import annotations

import sys


def main() -> None:
    print(
        "This repository root file is NOT the Lemma validator.\n"
        "  Run:  uv run lemma validator start\n"
        "  Docs: docs/validator.md\n"
        "  Legacy burn demo (educational only):  python examples/legacy_subnet_burn_validator.py --help\n",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
