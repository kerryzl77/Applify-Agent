"""URL normalization helpers."""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import quote, urlsplit, urlunsplit

_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")

_URL_TRANSLATION = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u00ad": "",
        "\u200b": "",
        "\u200c": "",
        "\u200d": "",
        "\u2060": "",
        "\ufeff": "",
        "\u00a0": " ",
    }
)


def normalize_url(raw: str) -> str:
    """Normalize URLs for safer fetching and parsing."""
    if not raw:
        return ""

    cleaned = unicodedata.normalize("NFKC", str(raw).strip())
    cleaned = cleaned.translate(_URL_TRANSLATION)
    cleaned = re.sub(r"\s+", "%20", cleaned)

    if not _SCHEME_RE.match(cleaned):
        cleaned = f"https://{cleaned}"

    try:
        parts = urlsplit(cleaned)
    except Exception:
        return cleaned

    netloc = parts.netloc
    path = parts.path
    if not netloc and path:
        if "/" in path:
            host, rest = path.split("/", 1)
            netloc = host
            path = f"/{rest}"
        else:
            netloc = path
            path = ""

    netloc = _idna_encode_netloc(netloc)
    path = quote(path, safe="/%:@-._~")
    query = quote(parts.query, safe="=&%:+-._~")
    fragment = quote(parts.fragment, safe="%+-._~")
    scheme = parts.scheme or "https"

    return urlunsplit((scheme, netloc, path, query, fragment))


def _idna_encode_netloc(netloc: str) -> str:
    if not netloc:
        return netloc

    if netloc.startswith("[") and "]" in netloc:
        return netloc

    auth = ""
    hostport = netloc
    if "@" in netloc:
        auth, hostport = netloc.rsplit("@", 1)

    host = hostport
    port = ""
    if ":" in hostport:
        host, port = hostport.rsplit(":", 1)

    try:
        host = host.encode("idna").decode("ascii")
    except Exception:
        pass

    rebuilt = host
    if port:
        rebuilt = f"{host}:{port}"
    if auth:
        rebuilt = f"{auth}@{rebuilt}"
    return rebuilt
