#!/usr/bin/env python3
"""
Environment variable helpers for WYGIWYH MCP configuration.
"""

from __future__ import annotations

import os

ENV_PREFIX = "WYGIWYH_MCP_"

# Backward compatibility: these settings used to be read from unprefixed
# environment variables before the WYGIWYH_MCP_ namespace was introduced. Fall
# back to the old names so existing deployments keep working unchanged.
LEGACY_ENV_NAMES = {
    "API_USERNAME": "API_USERNAME",
    "API_PASSWORD": "API_PASSWORD",
    "TOKEN": "MCP_TOKEN",
}


def get_env(name: str, default: str = "") -> str:
    prefixed_name = f"{ENV_PREFIX}{name}"
    value = os.getenv(prefixed_name)
    if value is not None:
        return value
    legacy_name = LEGACY_ENV_NAMES.get(name)
    if legacy_name is not None:
        legacy_value = os.getenv(legacy_name)
        if legacy_value is not None:
            return legacy_value
    return default


def get_env_bool(name: str, default: bool) -> bool:
    raw = get_env(name)
    if raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
