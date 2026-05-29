#!/usr/bin/env python3
"""
Environment variable helpers for WYGIWYH MCP configuration.
"""

from __future__ import annotations

import os

ENV_PREFIX = "WYGIWYH_MCP_"


def get_env(name: str, default: str = "") -> str:
    prefixed_name = f"{ENV_PREFIX}{name}"
    value = os.getenv(prefixed_name)
    if value is not None:
        return value
    return default


def get_env_bool(name: str, default: bool) -> bool:
    raw = get_env(name)
    if raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
