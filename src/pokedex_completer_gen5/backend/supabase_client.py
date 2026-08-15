from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SupabaseConfig:
    url: str
    publishable_key: str
    service_role_key: str | None = None


def load_supabase_config(require_service_role: bool = False) -> SupabaseConfig:
    url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    publishable_key = (
        os.getenv("SUPABASE_ANON_KEY")
        or os.getenv("SUPABASE_PUBLISHABLE_KEY")
        or os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY")
    )
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    missing = []
    if not url:
        missing.append("SUPABASE_URL")
    if not publishable_key:
        missing.append("SUPABASE_ANON_KEY or SUPABASE_PUBLISHABLE_KEY")
    if require_service_role and not service_role_key:
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    if missing:
        raise RuntimeError("Missing Supabase environment variables: " + ", ".join(missing))

    return SupabaseConfig(
        url=url,
        publishable_key=publishable_key,
        service_role_key=service_role_key,
    )


def create_supabase_client(use_service_role: bool = False) -> Any:
    """Create a Supabase client lazily.

    The `supabase` package is an optional backend dependency. Install with:

        uv sync --extra backend

    Service-role usage is for trusted server-side code only. Do not expose it to browsers,
    desktop clients, logs, or screenshots. Yes, this warning is here because humans are spicy.
    """
    try:
        from supabase import create_client
    except ImportError as exc:  # pragma: no cover - depends on optional extra.
        raise RuntimeError("Install backend dependencies with: uv sync --extra backend") from exc

    config = load_supabase_config(require_service_role=use_service_role)
    key = config.service_role_key if use_service_role else config.publishable_key
    if key is None:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required for service-role client")
    return create_client(config.url, key)
