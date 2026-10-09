from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv
from langfuse import get_client

load_dotenv()

logger = logging.getLogger(__name__)


def langfuse_enabled() -> bool:
    """Return True when tracing is enabled and configured."""

    enabled = os.getenv(
        "LANGFUSE_ENABLED",
        "false",
    ).strip().lower() in {"1", "true", "yes", "on"}

    if not enabled:
        return False

    required = (
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_BASE_URL",
    )

    missing = [
        name
        for name in required
        if not os.getenv(name, "").strip()
    ]

    if missing:
        logger.warning(
            "Langfuse is enabled but configuration is incomplete. "
            "Missing: %s",
            ", ".join(missing),
        )
        return False

    return True


def get_langfuse_client() -> Any | None:
    """Get the SDK v4 singleton client, or None when disabled."""

    if not langfuse_enabled():
        return None

    try:
        return get_client()
    except Exception:
        logger.exception(
            "Unable to initialize Langfuse; continuing without tracing."
        )
        return None


def flush_langfuse() -> None:
    """Flush queued observations, especially useful for CLI evaluation."""

    client = get_langfuse_client()

    if client is None:
        return

    try:
        client.flush()
    except Exception:
        logger.exception("Unable to flush Langfuse observations.")