#!/usr/bin/env python3
"""
MCP Server with HTTP Streamable transport for n8n

Copyright (c) 2025 ReNewator.com
All rights reserved.
"""

import json
from typing import Any
from starlette.applications import Starlette
from starlette.responses import Response, JSONResponse, StreamingResponse
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
import uvicorn
from server import app as mcp_server, get_tools_list
from resource_server_auth import OAuthResourceAuthenticator

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "WYGIWYH MCP Server"
SERVER_VERSION = "1.0.0"
resource_authenticator = OAuthResourceAuthenticator()


def _get_public_base_url(request: Request) -> str:
    configured = resource_authenticator.load_settings().public_base_url
    if configured:
        return configured
    return str(request.base_url).rstrip("/")


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
    """Validate incoming OAuth Bearer token for MCP access."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, None

    try:
        token = auth_header.split(" ", 1)[1].strip()
        if not token:
            return None, None
        claims = await resource_authenticator.validate_access_token(token)
        return token, claims
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc


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
    """Expose authorization server metadata for MCP clients."""
    metadata = await resource_authenticator.get_authorization_server_metadata()
    return JSONResponse(metadata)

async def handle_root_get(request: Request):
    """Handle GET requests to root - return SSE stream for initialization."""
    try:
        incoming_token, _claims = await authenticate_request(request)
    except RuntimeError as exc:
        return unauthorized_response(
            request,
            error="invalid_token",
            error_description=str(exc),
        )

    if not incoming_token:
        return unauthorized_response(request)
    
    print(f"SSE connection from {request.client}")
    
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
    """Handle POST requests to root - execute MCP methods."""
    try:
        incoming_token, incoming_claims = await authenticate_request(request)
    except RuntimeError as exc:
        return unauthorized_response(
            request,
            error="invalid_token",
            error_description=str(exc),
        )

    if not incoming_token:
        return unauthorized_response(request)
    
    try:
        body = await request.json()
        print(f"Received JSON-RPC request: {body.get('method', 'unknown')}")
        
        method = body.get("method")
        params = body.get("params", {})
        request_id = body.get("id")
        
        # Handle notifications (no id, no response needed)
        if request_id is None:
            print(f"Notification received: {method}")
            # Notifications don't get a response, just return 200
            return Response(status_code=200)
        
        # Handle different MCP methods
        if method == "initialize":
            result = {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                }
            }
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            })
        
        elif method == "tools/list":
            # Get tools from the MCP server
            tools_list = await get_tools_list()
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": tools_list
                }
            })
        
        elif method == "tools/call":
            # Call a tool
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            
            print(f"Calling tool: {tool_name} with args: {tool_args}")
            
            # Call the tool using the MCP server
            from server import call_tool_internal
            result = await call_tool_internal(
                tool_name,
                tool_args,
                incoming_access_token=incoming_token,
                incoming_claims=incoming_claims,
            )
            
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result)
                        }
                    ]
                }
            })
        
        else:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }, status_code=400)
    
    except Exception as e:
        print(f"Error handling request: {e}")
        import traceback
        traceback.print_exc()
        
        error_request_id = None
        try:
            body_dict = await request.json()
            error_request_id = body_dict.get("id")
        except:
            pass
        
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": error_request_id,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
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

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    ),
]

app = Starlette(routes=routes, middleware=middleware)

if __name__ == "__main__":
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
