"""Cross-validator judge profile agreement (optional HTTP peer probe).

When ``LEMMA_JUDGE_PROFILE_ATTEST_ENABLED=1``, the validator HTTP GETs each URL in
``LEMMA_JUDGE_PROFILE_ATTEST_PEER_URLS`` and checks the response parses to the same
``judge_profile_sha256`` as this process (already pinned via ``JUDGE_PROFILE_SHA256_EXPECTED``).

Peers typically run ``lemma validator judge-attest-serve`` or any endpoint returning the 64-char hex.
"""

from __future__ import annotations

import json
import re

import httpx
from loguru import logger

from lemma.common.config import LemmaSettings
from lemma.judge.profile import judge_profile_sha256

_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


def parse_peer_urls(raw: str | None) -> list[str]:
    if not raw:
        return []
    parts: list[str] = []
    for chunk in raw.replace("\n", ",").split(","):
        u = chunk.strip()
        if u:
            parts.append(u)
    return parts


def parse_peer_judge_hash(body: str) -> str | None:
    """Parse plaintext line or JSON ``{\"judge_profile_sha256\": \"...\"}``."""
    text = (body or "").strip()
    if not text:
        return None
    if text.startswith("{"):
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None
        if isinstance(data, dict):
            v = data.get("judge_profile_sha256")
            if v is not None:
                return _normalize_hash(str(v))
        return None
    line = text.splitlines()[0].strip()
    return _normalize_hash(line)


def _normalize_hash(s: str) -> str | None:
    h = s.strip()
    if h.lower().startswith("0x"):
        h = h[2:]
    h = h.strip().lower()
    if _HEX64.match(h):
        return h
    return None


def judge_profile_peer_check_errors(settings: LemmaSettings) -> list[str]:
    """Return fatal issues for startup / validator-check; empty if OK or feature off."""
    if not settings.lemma_judge_profile_attest_enabled:
        return []
    if settings.lemma_judge_profile_attest_allow_skip:
        return []

    urls = parse_peer_urls(settings.lemma_judge_profile_attest_peer_urls)
    if not urls:
        return [
            "LEMMA_JUDGE_PROFILE_ATTEST_ENABLED=1 requires LEMMA_JUDGE_PROFILE_ATTEST_PEER_URLS "
            "(comma-separated GET URLs; each must return this validator's judge_profile_sha256). "
            "Or set LEMMA_JUDGE_PROFILE_ATTEST_SKIP=1 for single-node dev.\n"
            "Tip: run `lemma validator judge-attest-serve` on peers and point URLs at "
            "http://HOST:PORT/lemma/judge_profile_sha256",
        ]

    my_hash = judge_profile_sha256(settings).strip().lower()
    if my_hash.startswith("0x"):
        my_hash = my_hash[2:]
    if not _HEX64.match(my_hash):
        return ["internal: local judge_profile_sha256 is not a 64-char hex string"]

    timeout = float(settings.lemma_judge_profile_attest_http_timeout_s or 15.0)
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            for url in urls:
                try:
                    r = client.get(url)
                    r.raise_for_status()
                except httpx.HTTPError as e:
                    return [f"judge profile attest: HTTP error for {url!r}: {e}"]
                peer_h = parse_peer_judge_hash(r.text)
                if not peer_h:
                    return [f"judge profile attest: could not parse 64-char hex from {url!r}"]
                if peer_h != my_hash:
                    return [
                        f"judge profile attest: {url!r} reports {peer_h[:16]}… "
                        f"but this validator is {my_hash[:16]}… — align judge stacks or URLs.",
                    ]
    except OSError as e:
        return [f"judge profile attest: network error: {e}"]

    logger.info(
        "judge profile attest: {} peer URL(s) match local judge_profile_sha256",
        len(urls),
    )
    return []


def serve_judge_profile_attest_forever(host: str, port: int, settings: LemmaSettings) -> None:
    """Serve ``GET /lemma/judge_profile_sha256`` (text/plain) and ``GET /health``."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    hash_hex = judge_profile_sha256(settings).strip().lower()
    if hash_hex.startswith("0x"):
        hash_hex = hash_hex[2:]

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0].rstrip("/") or "/"
            if path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"ok\n")
            elif path == "/lemma/judge_profile_sha256":
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write((hash_hex + "\n").encode("utf-8"))
            else:
                self.send_error(404, "Not Found")

        def log_message(self, fmt: str, *args: object) -> None:
            return

    srv = ThreadingHTTPServer((host, port), Handler)
    logger.info(
        "judge attest HTTP on http://{}:{}/lemma/judge_profile_sha256 (GET /health)",
        host,
        port,
    )
    srv.serve_forever()
