#!/usr/bin/env python3
"""
OAuth resource-server helpers for MCP HTTP authorization.
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
    introspection_url: str
    oauth_client_id: str
    oauth_client_secret: str
    required_scopes: tuple[str, ...]
    public_base_url: str
    metadata_ttl_seconds: int


class OAuthResourceAuthenticator:
    def __init__(self) -> None:
        self._metadata: dict[str, Any] | None = None
        self._metadata_loaded_at = 0.0

    def load_settings(self) -> ResourceServerSettings:
        authorization_server_url = get_env(
            "AUTHORIZATION_SERVER_URL",
            get_env("API_BASE_URL"),
        ).strip().rstrip("/")
        authorization_server_metadata_url = get_env(
            "AUTHORIZATION_SERVER_METADATA_URL",
            f"{authorization_server_url}/.well-known/oauth-authorization-server",
        ).strip()
        introspection_url = get_env(
            "OAUTH_INTROSPECTION_URL",
            f"{authorization_server_url}/oauth/introspect/",
        ).strip()
        required_scopes = tuple(
            scope
            for scope in get_env(
                "OAUTH_REQUIRED_SCOPES",
                "mcp",
            ).replace(",", " ").split()
            if scope
        )

        return ResourceServerSettings(
            authorization_server_url=authorization_server_url,
            authorization_server_metadata_url=authorization_server_metadata_url,
            introspection_url=introspection_url,
            oauth_client_id=get_env("OAUTH_CLIENT_ID").strip(),
            oauth_client_secret=get_env("OAUTH_CLIENT_SECRET").strip(),
            required_scopes=required_scopes,
            public_base_url=get_env("PUBLIC_BASE_URL").strip().rstrip("/"),
            metadata_ttl_seconds=int(get_env("OAUTH_METADATA_TTL_SECONDS", "300").strip()),
        )

    def get_error_message(self) -> str:
        settings = self.load_settings()
        missing = []
        if not settings.authorization_server_url:
            missing.append("WYGIWYH_MCP_AUTHORIZATION_SERVER_URL")
        if not settings.oauth_client_id:
            missing.append("WYGIWYH_MCP_OAUTH_CLIENT_ID")
        if not settings.oauth_client_secret:
            missing.append("WYGIWYH_MCP_OAUTH_CLIENT_SECRET")

        if missing:
            return "Error: " + ", ".join(missing) + " must be configured for MCP OAuth"

        return "Error: valid incoming Bearer token is required for MCP OAuth"

    async def get_authorization_server_metadata(self) -> dict[str, Any]:
        settings = self.load_settings()
        return await self._get_metadata(settings)

    async def validate_access_token(self, token: str) -> dict[str, Any]:
        settings = self.load_settings()
        if not settings.introspection_url:
            raise RuntimeError(
                "OAuth introspection is not configured. Set "
                "WYGIWYH_MCP_OAUTH_INTROSPECTION_URL."
            )
        if not settings.oauth_client_id or not settings.oauth_client_secret:
            raise RuntimeError(
                "OAuth introspection credentials are not configured. Set "
                "WYGIWYH_MCP_OAUTH_CLIENT_ID and WYGIWYH_MCP_OAUTH_CLIENT_SECRET."
            )

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                settings.introspection_url,
                data={"token": token},
                auth=(settings.oauth_client_id, settings.oauth_client_secret),
            )
            response.raise_for_status()
            claims = response.json()

        if not claims.get("active"):
            raise RuntimeError("Access token is inactive")

        self._validate_scopes(settings.required_scopes, claims)
        return claims

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

    def _validate_scopes(
        self,
        required_scopes: tuple[str, ...],
        claims: dict[str, Any],
    ) -> None:
        if not required_scopes:
            return

        token_scopes = claims.get("scope", "")
        scope_set = {scope for scope in str(token_scopes).split() if scope}
        missing_scopes = [scope for scope in required_scopes if scope not in scope_set]
        if missing_scopes:
            raise RuntimeError(
                "Access token is missing required scopes: " + ", ".join(missing_scopes)
            )
