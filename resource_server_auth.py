#!/usr/bin/env python3
"""
OAuth resource-server helpers for MCP HTTP authorization.

The MCP server does not validate access tokens itself. Every tool call forwards
the incoming Bearer token to the WYGIWYH API, which authenticates it, so there
is no second validation here and the MCP server needs no credentials of its own.
This module only resolves the OAuth metadata the MCP server advertises to clients
so they can run the authorization-code flow against WYGIWYH.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from env_config import get_env


@dataclass(frozen=True)
class ResourceServerSettings:
    authorization_server_url: str
    authorization_server_metadata_url: str
    required_scopes: tuple[str, ...]
    public_base_url: str
    metadata_ttl_seconds: int


class OAuthResourceAuthenticator:
    def __init__(self) -> None:
        self._metadata: dict[str, Any] | None = None
        self._metadata_loaded_at = 0.0

    def load_settings(self) -> ResourceServerSettings:
        authorization_server_url = (
            get_env("AUTHORIZATION_SERVER_URL", get_env("API_BASE_URL"))
            .strip()
            .rstrip("/")
        )
        authorization_server_metadata_url = get_env(
            "AUTHORIZATION_SERVER_METADATA_URL",
            f"{authorization_server_url}/.well-known/oauth-authorization-server",
        ).strip()
        required_scopes = tuple(
            scope
            for scope in get_env("OAUTH_REQUIRED_SCOPES", "mcp").replace(",", " ").split()
            if scope
        )

        return ResourceServerSettings(
            authorization_server_url=authorization_server_url,
            authorization_server_metadata_url=authorization_server_metadata_url,
            required_scopes=required_scopes,
            public_base_url=get_env("PUBLIC_BASE_URL").strip().rstrip("/"),
            metadata_ttl_seconds=int(get_env("OAUTH_METADATA_TTL_SECONDS", "300").strip()),
        )

    async def get_authorization_server_metadata(self) -> dict[str, Any]:
        settings = self.load_settings()
        return await self._get_metadata(settings)

    async def _get_metadata(self, settings: ResourceServerSettings) -> dict[str, Any]:
        if not settings.authorization_server_metadata_url:
            raise RuntimeError(
                "OAuth authorization server metadata is not configured. Set "
                "WYGIWYH_MCP_AUTHORIZATION_SERVER_METADATA_URL."
            )

        if self._metadata and not self._is_stale(self._metadata_loaded_at, settings):
            return self._metadata

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(settings.authorization_server_metadata_url)
            response.raise_for_status()
            self._metadata = response.json()
            self._metadata_loaded_at = time.time()
            return self._metadata

    def _is_stale(self, loaded_at: float, settings: ResourceServerSettings) -> bool:
        return time.time() - loaded_at > settings.metadata_ttl_seconds
