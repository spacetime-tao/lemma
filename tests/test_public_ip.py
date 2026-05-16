"""Public IP discovery for miner axon."""

from unittest.mock import MagicMock

import pytest


def test_discover_public_ipv4_success(monkeypatch: pytest.MonkeyPatch) -> None:
    import lemma.miner.public_ip as pi

    calls = []

    def fake_get(url: str, params: dict | None = None, timeout: float = 5.0):
        calls.append(url)
        r = MagicMock()
        r.raise_for_status = MagicMock()
        r.text = "203.0.113.7\n"
        return r

    monkeypatch.setattr(pi.httpx, "get", fake_get)
    assert pi.discover_public_ipv4() == "203.0.113.7"
    assert "ipify" in calls[0]


def test_discover_public_ipv4_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    import lemma.miner.public_ip as pi

    def fake_get(url: str, params: dict | None = None, timeout: float = 5.0):
        r = MagicMock()
        r.raise_for_status = MagicMock()
        if "ipify" in url:
            r.text = "not-an-ip"
        else:
            r.text = "198.51.100.2"
        return r

    monkeypatch.setattr(pi.httpx, "get", fake_get)
    assert pi.discover_public_ipv4() == "198.51.100.2"


def test_discover_public_ipv4_none(monkeypatch: pytest.MonkeyPatch) -> None:
    import lemma.miner.public_ip as pi

    def fake_get(url: str, params: dict | None = None, timeout: float = 5.0):
        r = MagicMock()
        r.raise_for_status.side_effect = OSError("network")
        return r

    monkeypatch.setattr(pi.httpx, "get", fake_get)
    assert pi.discover_public_ipv4() is None
