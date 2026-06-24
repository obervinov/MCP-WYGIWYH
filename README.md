# [WYGIWYH](https://github.com/eitchtee/WYGIWYH) API MCP Server


A production-ready Model Context Protocol (MCP) server that provides a universal interface to the WYGIWYH expense tracking API. The server dynamically generates 75 MCP tools from an OpenAPI specification, enabling AI agents and automation platforms like n8n to interact with the expense tracking system through standardized tool calls.

Original repo of [WYGIWYH](https://github.com/eitchtee/WYGIWYH) 

## ✨ Features

- 🔄 **Dynamic Tool Generation** - Automatically generates 75 MCP tools from OpenAPI specification
- 🔐 **Secure Authentication** - MCP-spec OAuth for MCP endpoints + incoming bearer, Basic, or static Bearer auth for WYGIWYH API access
- 🚀 **HTTP Streamable Transport** - Full compatibility with n8n and other MCP clients
- 🐳 **Production-Ready Docker** - Optimized multi-stage build with health checks
- ⚡ **Async/Await** - Efficient non-blocking API communication
- 📊 **Comprehensive API Coverage** - All WYGIWYH API endpoints exposed as tools

## 🎯 Use Cases

- Automate expense tracking workflows with n8n
- Build AI assistants that manage financial data
- Create custom integrations with WYGIWYH API
- Implement voice-controlled expense logging
- Develop automated reporting systems

## 📦 Quick Start

### Prerequisites

- Docker & Docker Compose
- WYGIWYH API credentials or OAuth client settings

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ReNewator/MCP-WYGIWYH.git
   cd MCP-WYGIWYH
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   # Set WYGIWYH_MCP_API_BASE_URL and OAuth settings for your deployment
   ```

3. **Deploy with Docker**
   ```bash
   ./deploy.sh
   ```

   Or manually:
   ```bash
   docker-compose up -d
   ```

4. **Verify deployment**
   ```bash
   curl http://localhost:5000/health
   ```

## 🔧 Configuration

Create a `.env` file with the following variables:

```env
# WYGIWYH API connection
WYGIWYH_MCP_API_BASE_URL=https://your-wygiwyh.example.com
WYGIWYH_MCP_API_AUTH_MODE=incoming_bearer

# OAuth authorization server (WYGIWYH) that MCP clients authenticate against
WYGIWYH_MCP_AUTHORIZATION_SERVER_URL=https://your-wygiwyh.example.com
WYGIWYH_MCP_AUTHORIZATION_SERVER_METADATA_URL=
WYGIWYH_MCP_OAUTH_REQUIRED_SCOPES=mcp

# Public URL clients use to reach this MCP server (required)
WYGIWYH_MCP_PUBLIC_BASE_URL=https://your-mcp.example.com
WYGIWYH_MCP_OAUTH_METADATA_TTL_SECONDS=300

# Optional fallback auth modes for direct API access (instead of incoming_bearer)
WYGIWYH_MCP_API_USERNAME=your_email@example.com
WYGIWYH_MCP_API_PASSWORD=your_password_here
WYGIWYH_MCP_API_BEARER_TOKEN=your_access_token_here
```

The server reads only the `WYGIWYH_MCP_*` namespace.

In the default `incoming_bearer` mode, the MCP client authenticates against `WYGIWYH`, sends that bearer token to the MCP server, and the MCP server forwards the same token to the WYGIWYH API, **which validates it**. The MCP server does not introspect or otherwise validate the token itself, so it needs no OAuth client credentials of its own.

> Because validation is delegated to the WYGIWYH API, every WYGIWYH `/api/` route must require authentication — there is no second check in the MCP server.

Remote MCP OAuth flow:

1. MCP client hits the MCP server without a token
2. MCP server returns `401` with `resource_metadata`
3. MCP client discovers `WYGIWYH` auth metadata
4. MCP client registers dynamically (DCR) and opens the browser against `WYGIWYH`
5. `WYGIWYH` handles login/consent and issues an access token
6. MCP client calls the MCP server with `Authorization: Bearer <token>`

Minimal container example:

```bash
podman run --rm -it \
  -p 5000:5000 \
  -e WYGIWYH_MCP_API_BASE_URL=https://your-wygiwyh.example.com \
  -e WYGIWYH_MCP_API_AUTH_MODE=incoming_bearer \
  -e WYGIWYH_MCP_AUTHORIZATION_SERVER_URL=https://your-wygiwyh.example.com \
  -e WYGIWYH_MCP_PUBLIC_BASE_URL=https://your-mcp.example.com \
  wygiwyh-mcp-server:latest
```

## 🌐 n8n Integration

Configure the n8n MCP Client node:

- **Endpoint:** `http://your-server:5000/`
- **Transport:** HTTP Streamable
- **Authentication:** OAuth 2.0 / Bearer token from `WYGIWYH`

## 🛠️ Available Tools

The server exposes **75 MCP tools** organized by category:

### Account Management
- `account-groups_*` - Account group operations (6 tools)
- `accounts_*` - Account CRUD operations (6 tools)

### Transaction Management
- `transactions_*` - Transaction operations (6 tools)
- `recurring-transactions_*` - Recurring transaction management (6 tools)
- `installment-plans_*` - Installment plan handling (6 tools)

### Financial Tools
- `categories_*` - Expense category management (6 tools)
- `tags_*` - Transaction tagging (6 tools)
- `currencies_*` - Currency management (6 tools)
- `exchange-rates_*` - Exchange rate operations (6 tools)

### Investment Features
- `dca_*` - Dollar-cost averaging strategies (15 tools)
- `entities_*` - Entity management (6 tools)

Use the `tools/list` method to see all available tools with their schemas.

## 📁 Project Structure

```
.
├── mcp_sse_server.py      # Main MCP server with HTTP Streamable
├── server.py              # Core MCP implementation
├── test_server.py         # Validation script
├── Dockerfile             # Production Docker image
├── docker-compose.yml     # Docker Compose config
├── deploy.sh              # Automated deployment
├── requirements.txt       # Python dependencies
├── DEPLOYMENT.md          # Detailed deployment guide
├── PROJECT.md             # Technical documentation
└── attached_assets/
    └── WYGIWYH API.yaml   # OpenAPI specification
```

## 🚀 Deployment

### Docker (Recommended)

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop server
docker-compose down
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wygiwyh-mcp-server
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: mcp-server
        image: wygiwyh-mcp-server:latest
        ports:
        - containerPort: 5000
        env:
        - name: WYGIWYH_MCP_API_USERNAME
          valueFrom:
            secretKeyRef:
              name: wygiwyh-secrets
              key: api-username
```

### Cloud Platforms

- **AWS ECS/Fargate** - Use the Docker image with environment variables
- **Google Cloud Run** - Deploy as container with secrets management
- **Azure Container Instances** - Direct deployment from Docker Hub

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed cloud deployment instructions.

## 🧪 Testing

Run the validation script to verify the setup:

```bash
python test_server.py
```

This displays all 75 generated MCP tools grouped by category.

## 📊 API Endpoints

- `POST /` - MCP JSON-RPC endpoint (requires OAuth Bearer token)
- `GET /.well-known/oauth-protected-resource` - MCP protected resource metadata
- `GET /.well-known/oauth-authorization-server` - proxied authorization server metadata
- `GET /health` - Health check (no authentication)

## 🔒 Security Features

- ✅ OAuth Bearer authentication for MCP access
- ✅ Incoming bearer passthrough to WYGIWYH API
- ✅ Basic or static Bearer fallback modes for WYGIWYH API requests
- ✅ Non-root container user
- ✅ Secrets managed via environment variables
- ✅ No exposed credentials in logs

## 🏗️ Architecture

### Dynamic Tool Generation

The server automatically generates MCP tools from the OpenAPI specification:

1. Parses WYGIWYH API OpenAPI YAML
2. Converts schemas to JSON Schema format
3. Creates Tool objects for all operations
4. Handles `allOf` merging for complex types
5. Exposes tools via MCP protocol

**Benefits:**
- Single source of truth (OpenAPI spec)
- Automatic updates when API changes
- Zero manual endpoint definitions
- Consistent tool schemas

### Authentication Flow

```
┌─────────────┐     Bearer Token     ┌─────────────┐
│   n8n/MCP   │ ──────────────────> │  MCP Server │
│   Client    │                      │             │
└─────────────┘                      └─────────────┘
                                            │
                                           │ Basic / Bearer / OIDC access token
                                            ▼
                                     ┌─────────────┐
                                     │  WYGIWYH    │
                                     │     API     │
                                     └─────────────┘
```

The MCP server itself is only an OAuth resource server: it advertises metadata
and forwards the bearer token. The authorization-code + PKCE flow (and any
dynamic client registration / token refresh) is run by the **MCP client**
against `WYGIWYH` — the server never holds client credentials or refresh tokens.

## 🐛 Troubleshooting

### Server won't start

```bash
# Check logs
docker-compose logs

# Verify environment
cat .env
```

### Authentication errors

- If `WYGIWYH_MCP_API_AUTH_MODE=basic`, ensure `WYGIWYH_MCP_API_USERNAME` and `WYGIWYH_MCP_API_PASSWORD` are correct
- If `WYGIWYH_MCP_API_AUTH_MODE=bearer`, ensure `WYGIWYH_MCP_API_BEARER_TOKEN` is valid and not expired
- If `WYGIWYH_MCP_API_AUTH_MODE=incoming_bearer`, ensure the MCP client obtained a valid `WYGIWYH` token and sends it as `Authorization: Bearer ...`. The token is forwarded to the WYGIWYH API, so a 401/403 from a tool means WYGIWYH rejected the token.

### Connection refused

```bash
# Check server status
docker-compose ps

# Test health endpoint
curl http://localhost:5000/health
```

## 📚 Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Comprehensive deployment guide
- [PROJECT.md](PROJECT.md) - Technical architecture documentation

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## 📄 License

Copyright (c) 2025 ReNewator.com. All rights reserved.

## 🔗 Links

- [WYGIWYH API Documentation](https://fin.vigitix.com/api/docs/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [n8n Automation](https://n8n.io/)

## 💬 Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation
- Review deployment logs

---

**Built with ❤️ by ReNewator.com**
