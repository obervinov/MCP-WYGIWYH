# Production Deployment Guide

**Copyright (c) 2025 ReNewator.com**

## Quick Start

### 1. Prerequisites
- Docker & Docker Compose installed
- WYGIWYH API credentials or OAuth client settings

### 2. Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
WYGIWYH_MCP_API_BASE_URL=https://your-wygiwyh.example.com
WYGIWYH_MCP_API_AUTH_MODE=incoming_bearer
WYGIWYH_MCP_AUTHORIZATION_SERVER_URL=https://your-wygiwyh.example.com
WYGIWYH_MCP_AUTHORIZATION_SERVER_METADATA_URL=
WYGIWYH_MCP_OAUTH_REQUIRED_SCOPES=mcp
WYGIWYH_MCP_PUBLIC_BASE_URL=https://your-mcp.example.com
```

### 3. Deploy

Run the deployment script:

```bash
./deploy.sh
```

Or manually with Docker Compose:

```bash
docker-compose up -d
```

### Remote MCP OAuth flow

The default deployment uses `WYGIWYH` as the OAuth authorization server. The MCP
client authenticates against `WYGIWYH` and sends the resulting bearer token to
the MCP server, which forwards it to the WYGIWYH API for validation — the MCP
server holds no OAuth credentials of its own.

```env
WYGIWYH_MCP_API_AUTH_MODE=incoming_bearer
WYGIWYH_MCP_AUTHORIZATION_SERVER_URL=https://your-wygiwyh.example.com
WYGIWYH_MCP_OAUTH_REQUIRED_SCOPES=mcp
WYGIWYH_MCP_PUBLIC_BASE_URL=https://your-mcp.example.com
```

MCP clients that support dynamic client registration self-register against
`WYGIWYH`; no OAuth application needs to be pre-created for the MCP server.

Container example:

```bash
podman run --rm -it \
  -p 5000:5000 \
  -e WYGIWYH_MCP_API_BASE_URL=https://your-wygiwyh.example.com \
  -e WYGIWYH_MCP_API_AUTH_MODE=incoming_bearer \
  -e WYGIWYH_MCP_AUTHORIZATION_SERVER_URL=https://your-wygiwyh.example.com \
  -e WYGIWYH_MCP_PUBLIC_BASE_URL=https://your-mcp.example.com \
  wygiwyh-mcp-server:latest
```

## Endpoints

- **Main endpoint:** `http://localhost:5000/`
- **Health check:** `http://localhost:5000/health`

## n8n Integration

Configure n8n MCP Client:
- **URL:** `http://your-server:5000/`
- **Transport:** HTTP Streamable
- **Authentication:** OAuth 2.0 / Bearer token from `WYGIWYH`

## Management Commands

```bash
# View logs
docker-compose logs -f

# Restart server
docker-compose restart

# Stop server
docker-compose down

# Rebuild and restart
docker-compose up -d --build

# View container status
docker-compose ps
```

## Production Considerations

### Security
- ✅ Runs as non-root user
- ✅ Bearer token authentication
- ✅ No exposed secrets in logs
- ✅ Health checks enabled

### Monitoring
- Health check endpoint: `/health`
- Docker health checks configured
- Automatic container restart on failure

### Performance
- Multi-stage Docker build
- Optimized Python dependencies
- Async/await request handling
- Connection pooling via httpx

## Cloud Deployment

### Docker Hub
```bash
# Tag image
docker tag wygiwyh-mcp-server:latest your-username/wygiwyh-mcp-server:latest

# Push to Docker Hub
docker push your-username/wygiwyh-mcp-server:latest
```

### AWS ECS / Azure Container Instances / Google Cloud Run

Use the built image with environment variables:
- `WYGIWYH_MCP_API_BASE_URL`
- `WYGIWYH_MCP_API_AUTH_MODE`
- `WYGIWYH_MCP_API_USERNAME`
- `WYGIWYH_MCP_API_PASSWORD`
- `WYGIWYH_MCP_API_BEARER_TOKEN`
- `WYGIWYH_MCP_AUTHORIZATION_SERVER_URL`
- `WYGIWYH_MCP_AUTHORIZATION_SERVER_METADATA_URL`
- `WYGIWYH_MCP_OAUTH_REQUIRED_SCOPES`
- `WYGIWYH_MCP_PUBLIC_BASE_URL`

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wygiwyh-mcp-server
spec:
  replicas: 2
  selector:
    matchLabels:
      app: wygiwyh-mcp-server
  template:
    metadata:
      labels:
        app: wygiwyh-mcp-server
    spec:
      containers:
      - name: mcp-server
        image: wygiwyh-mcp-server:latest
        ports:
        - containerPort: 5000
        env:
        - name: WYGIWYH_MCP_API_BASE_URL
          value: https://your-wygiwyh.example.com
        - name: WYGIWYH_MCP_API_AUTH_MODE
          value: incoming_bearer
        - name: WYGIWYH_MCP_AUTHORIZATION_SERVER_URL
          value: https://your-wygiwyh.example.com
        - name: WYGIWYH_MCP_PUBLIC_BASE_URL
          value: https://your-mcp.example.com
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 30
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs

# Verify .env file
cat .env
```

### Connection refused
```bash
# Check if container is running
docker-compose ps

# Check health
curl http://localhost:5000/health
```

### API authentication errors
- If `WYGIWYH_MCP_API_AUTH_MODE=basic`, verify `WYGIWYH_MCP_API_USERNAME` and `WYGIWYH_MCP_API_PASSWORD`
- If `WYGIWYH_MCP_API_AUTH_MODE=bearer`, verify `WYGIWYH_MCP_API_BEARER_TOKEN`
- If `WYGIWYH_MCP_API_AUTH_MODE=incoming_bearer`, verify the MCP client obtained a valid `WYGIWYH` token and sends it as `Authorization: Bearer ...`; the token is forwarded to the WYGIWYH API, so a 401/403 from a tool means WYGIWYH rejected it

## Available Tools

The server exposes 75 MCP tools for WYGIWYH API:
- Account management (groups, accounts)
- Transaction management
- Categories & tags
- Currencies & exchange rates
- Recurring transactions & installments
- DCA strategies
- And more...

Use `tools/list` method to see all available tools.
