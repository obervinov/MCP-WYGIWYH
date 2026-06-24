#!/usr/bin/env python3
"""
MCP Server with HTTP Streamable transport for n8n

Copyright (c) 2025 ReNewator.com
All rights reserved.
"""

import json
import logging
from typing import Any
from starlette.applications import Starlette
from starlette.responses import Response, JSONResponse, StreamingResponse
from starlette.routing import Route
from starlette.requests import Request
import uvicorn
from server import app as mcp_server, get_tools_list
from resource_server_auth import OAuthResourceAuthenticator

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "WYGIWYH MCP Server"
SERVER_VERSION = "1.0.0"
resource_authenticator = OAuthResourceAuthenticator()


def _get_public_base_url(request: Request) -> str:
    # Never derive security-relevant URLs from the request Host header: a client
    # could spoof it and steer the OAuth discovery chain. Require explicit config.
    configured = resource_authenticator.load_settings().public_base_url
    if not configured:
        raise RuntimeError(
            "WYGIWYH_MCP_PUBLIC_BASE_URL is not configured."
        )
    return configured


def _build_protected_resource_metadata_url(request: Request) -> str:
    return f"{_get_public_base_url(request)}/.well-known/oauth-protected-resource"


def _build_www_authenticate_header(
    request: Request,
    *,
    error: str | None = None,
    error_description: str | None = None,
) -> str:
    parts = [
        'Bearer realm="WYGIWYH MCP Server"',
        f'resource_metadata="{_build_protected_resource_metadata_url(request)}"',
    ]
    if error:
        parts.append(f'error="{error}"')
    if error_description:
        escaped = error_description.replace("\\", "\\\\").replace('"', '\\"')
        parts.append(f'error_description="{escaped}"')
    return ", ".join(parts)


async def authenticate_request(request: Request) -> tuple[str | None, dict[str, Any] | None]:
    """Extract the incoming OAuth Bearer token.

    Validation is delegated to the WYGIWYH API, which authenticates the token on
    every forwarded request, so the MCP server does not introspect it here (and
    needs no resource-server credentials of its own). A missing token still gets
    a 401 + WWW-Authenticate challenge so the client starts the OAuth flow.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, None

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return None, None
    return token, {}


def unauthorized_response(
    request: Request,
    *,
    error: str | None = None,
    error_description: str | None = None,
) -> Response:
    return Response(
        content='{"error": "Unauthorized"}',
        status_code=401,
        media_type="application/json",
        headers={
            "WWW-Authenticate": _build_www_authenticate_header(
                request,
                error=error,
                error_description=error_description,
            )
        },
    )

async def health_check(request: Request):
    """Health check endpoint - no auth required."""
    return JSONResponse({
        "status": "ok",
        "server": SERVER_NAME,
        "transport": "HTTP Streamable",
        "auth": "OAuth 2.1 Bearer token required for MCP endpoints",
    })


async def protected_resource_metadata(request: Request):
    """Expose OAuth protected resource metadata for MCP clients."""
    settings = resource_authenticator.load_settings()
    metadata = {
        "resource": f"{_get_public_base_url(request)}/",
        "authorization_servers": (
            [settings.authorization_server_url]
            if settings.authorization_server_url
            else []
        ),
        "scopes_supported": list(settings.required_scopes),
        "bearer_methods_supported": ["header"],
        "resource_name": SERVER_NAME,
        "resource_documentation": f"{_get_public_base_url(request)}/",
    }
    return JSONResponse(metadata)


async def authorization_server_metadata(request: Request):
    """Proxy the WYGIWYH authorization server metadata for MCP clients."""
    try:
        metadata = await resource_authenticator.get_authorization_server_metadata()
    except Exception:
        logger.exception("Failed to fetch authorization server metadata")
        return JSONResponse(
            {"error": "upstream_metadata_unavailable",
             "error_description": "Could not retrieve WYGIWYH authorization server metadata."},
            status_code=502,
        )
    return JSONResponse(metadata)

async def handle_root_get(request: Request):
    """Handle GET requests to root - return SSE stream for initialization."""
    incoming_token, _ = await authenticate_request(request)
    if not incoming_token:
        return unauthorized_response(request)

    logger.info("SSE connection from %s", request.client)
    
    # Return SSE stream with server info
    async def event_stream():
        # Send initialize event
        yield f"event: message\n"
        yield f"data: {json.dumps({'jsonrpc': '2.0', 'method': 'initialize', 'params': {'protocolVersion': PROTOCOL_VERSION, 'capabilities': {}, 'serverInfo': {'name': SERVER_NAME, 'version': SERVER_VERSION}}})}\n\n"
        
        # Keep connection alive
        import asyncio
        while True:
            await asyncio.sleep(30)
            yield f": keepalive\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

async def handle_root_post(request: Request):
    """Handle POST requests to root - execute MCP JSON-RPC methods."""
    incoming_token, _ = await authenticate_request(request)
    if not incoming_token:
        return unauthorized_response(request)

    # Parse the JSON-RPC body exactly once.
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"jsonrpc": "2.0", "id": None,
             "error": {"code": -32700, "message": "Parse error"}},
            status_code=400,
        )
    if not isinstance(body, dict):
        # Batch requests are not supported by this server.
        return JSONResponse(
            {"jsonrpc": "2.0", "id": None,
             "error": {"code": -32600, "message": "Invalid Request"}},
            status_code=400,
        )

    method = body.get("method")
    params = body.get("params") or {}
    request_id = body.get("id")

    # Notifications (no id) get no response body.
    if request_id is None:
        logger.info("Notification received: %s", method)
        return Response(status_code=200)

    try:
        if method == "initialize":
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                },
            })

        if method == "tools/list":
            tools_list = await get_tools_list()
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": tools_list},
            })

        if method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            logger.info("Calling tool: %s", tool_name)

            from server import call_tool_internal
            result = await call_tool_internal(
                tool_name,
                tool_args,
                incoming_access_token=incoming_token,
            )
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result)}]
                },
            })

        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }, status_code=400)

    except Exception:
        # Log the detail server-side; return a generic error to the client.
        logger.exception(
            "Error handling JSON-RPC request (id=%s, method=%s)", request_id, method
        )
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32603, "message": "Internal error"},
        }, status_code=500)

routes = [
    Route("/", handle_root_get, methods=["GET"]),
    Route("/", handle_root_post, methods=["POST"]),
    Route(
        "/.well-known/oauth-protected-resource",
        protected_resource_metadata,
        methods=["GET"],
    ),
    Route(
        "/.well-known/oauth-authorization-server",
        authorization_server_metadata,
        methods=["GET"],
    ),
    Route("/health", health_check, methods=["GET"]),
]

# No CORS middleware: this is a machine-to-machine MCP endpoint, not a browser
# API. A wildcard origin with credentials would let any site read finance data.
app = Starlette(routes=routes)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Fail fast on missing required config rather than deriving public URLs from
    # the request Host header at runtime.
    if not resource_authenticator.load_settings().public_base_url:
        raise SystemExit(
            "WYGIWYH_MCP_PUBLIC_BASE_URL is required (the public URL clients use "
            "to reach this MCP server)."
        )

    print("\n" + "="*60)
    print("Starting WYGIWYH MCP Server with HTTP Streamable")
    print("="*60)
    print(f"Server: http://0.0.0.0:5000")
    print("\nEndpoints:")
    print("  GET  / - SSE stream for MCP")
    print("  POST / - JSON-RPC MCP methods")
    print("  GET  /.well-known/oauth-protected-resource - OAuth resource metadata")
    print("  GET  /.well-known/oauth-authorization-server - OAuth AS metadata proxy")
    print("  GET  /health - Health check (no auth)")
    print("\nAuthentication:")
    print("  MCP clients should authenticate with OAuth/OIDC and send a Bearer token")
    print("="*60 + "\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        log_level="info"
    )
