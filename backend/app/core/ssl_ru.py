"""TLS helpers for hosts that use the Russian Trusted Root CA."""
from __future__ import annotations

import ssl
from functools import lru_cache
from pathlib import Path

_CERTS_DIR = Path(__file__).resolve().parents[2] / "certs"
_RU_CERT_NAMES = (
    "russian_trusted_root_ca.crt",
    "russian_trusted_sub_ca.crt",
)


@lru_cache
def russian_trusted_ssl_context() -> ssl.SSLContext:
    """System trust store plus Минцифры roots (needed for platform-api2.max.ru)."""
    ctx = ssl.create_default_context()
    blobs: list[str] = []
    for name in _RU_CERT_NAMES:
        path = _CERTS_DIR / name
        if path.is_file():
            blobs.append(path.read_text(encoding="utf-8"))
    if blobs:
        ctx.load_verify_locations(cadata="\n".join(blobs))
    return ctx
