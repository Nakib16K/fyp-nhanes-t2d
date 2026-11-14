"""Production-aware but fail-closed API CORS configuration; no input storage."""
from urllib.parse import urlsplit


class ConfigurationError(ValueError):
    """Unsafe CORS configuration."""


def allowed_origins(raw: str | None) -> list[str]:
    """Return exact frontend origins, defaulting to local development.

    Set FYP_CORS_ORIGINS to the frontend's HTTPS origin for deployment.
    Wildcards and credentialed origins are not supported.
    """
    if raw is None:
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    parts = [s.strip() for s in raw.split(",")]
    if not parts or any(not p for p in parts):
        raise ConfigurationError("Empty CORS origin")
    out = []
    for origin in parts:
        url = urlsplit(origin)
        if url.scheme not in ("http", "https") or not url.netloc:
            raise ConfigurationError("CORS origin must be an absolute URL")
        if url.username or url.password or url.path or url.query or url.fragment or "*" in origin:
            raise ConfigurationError("Only exact CORS origins allowed")
        if url.scheme == "http" and url.hostname not in ("localhost", "127.0.0.1", "[::1]", "::1"):
            raise ConfigurationError("Non-localhost CORS origin must use HTTPS")
        if origin not in out:
            out.append(origin)
    return out
