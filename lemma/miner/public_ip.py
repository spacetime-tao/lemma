"""Optional public IPv4 discovery for miner axon advertisement.

Does not configure firewalls or routers — only fills in the address to advertise.
"""

from __future__ import annotations

import ipaddress
from typing import Final

import httpx

_IP_SOURCES: Final[tuple[tuple[str, dict[str, str] | None], ...]] = (
    ("https://api.ipify.org", {"format": "text"}),
    ("https://icanhazip.com", None),
)


def discover_public_ipv4(timeout_s: float = 5.0) -> str | None:
    """Return this host's public IPv4 if reachable discovery services agree, else ``None``."""
    for url, params in _IP_SOURCES:
        try:
            r = httpx.get(url, params=params or {}, timeout=timeout_s)
            r.raise_for_status()
            text = r.text.strip().split()[0] if r.text.strip() else ""
            ipaddress.IPv4Address(text)
            return text
        except Exception:
            continue
    return None
