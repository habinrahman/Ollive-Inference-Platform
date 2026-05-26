from __future__ import annotations

import ssl


def build_ssl_context(*, enabled: bool, mode: str) -> ssl.SSLContext | bool:
    if not enabled:
        return False

    normalized_mode = (mode or "require").strip().lower()
    if normalized_mode == "disable":
        # Backwards-compatible behavior: DATABASE_SSL=true without an explicit
        # mode should still create an encrypted Supabase connection.
        normalized_mode = "require"

    if normalized_mode == "verify-full":
        return ssl.create_default_context()

    if normalized_mode == "require":
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    raise ValueError("DATABASE_SSL_MODE must be one of: disable, require, verify-full")
