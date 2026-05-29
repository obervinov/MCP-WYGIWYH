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
WYGIWYH_MCP_OAUTH_INTROSPECTION_URL=
# Must match the OAuth app configured in WYGIWYH
WYGIWYH_MCP_OAUTH_CLIENT_ID=mcp-wygiwyh
WYGIWYH_MCP_OAUTH_CLIENT_SECRET=change-me
WYGIWYH_MCP_OAUTH_REQUIRED_SCOPES=mcp
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

The default deployment uses `WYGIWYH` as the OAuth authorization server:

```env
WYGIWYH_MCP_API_AUTH_MODE=incoming_bearer
WYGIWYH_MCP_AUTHORIZATION_SERVER_URL=https://your-wygiwyh.example.com
WYGIWYH_MCP_OAUTH_CLIENT_ID=mcp-wygiwyh
WYGIWYH_MCP_OAUTH_CLIENT_SECRET=change-me
WYGIWYH_MCP_OAUTH_REQUIRED_SCOPES=mcp
```

On the `WYGIWYH` side, configure the matching bootstrap env so the client exists after startup:

```env
MCP_OAUTH_CLIENT_ID=mcp-wygiwyh
MCP_OAUTH_CLIENT_SECRET=change-me
MCP_OAUTH_REDIRECT_URIS=http://127.0.0.1:8765/callback
```

`WYGIWYH` startup now runs `python manage.py setup_oauth` after `migrate`, so you do not need to create the OAuth application manually in Django admin.

Container example:

```bash
podman run --rm -it \
  -p 5000:5000 \
  -e WYGIWYH_MCP_API_BASE_URL=https://your-wygiwyh.example.com \
  -e WYGIWYH_MCP_API_AUTH_MODE=incoming_bearer \
  -e WYGIWYH_MCP_AUTHORIZATION_SERVER_URL=https://your-wygiwyh.example.com \
  -e WYGIWYH_MCP_OAUTH_CLIENT_ID=mcp-wygiwyh \
  -e WYGIWYH_MCP_OAUTH_CLIENT_SECRET=change-me \
  zot.charafee.cfd:5000/mcp-wygiwyh:keycloak-jwt-mvp
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
- `WYGIWYH_MCP_OAUTH_INTROSPECTION_URL`
- `WYGIWYH_MCP_OAUTH_CLIENT_ID`
- `WYGIWYH_MCP_OAUTH_CLIENT_SECRET`
- `WYGIWYH_MCP_OAUTH_REQUIRED_SCOPES`

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
        - name: WYGIWYH_MCP_OAUTH_CLIENT_ID
          valueFrom:
            secretKeyRef:
              name: wygiwyh-secrets
              key: oauth-client-id
        - name: WYGIWYH_MCP_OAUTH_CLIENT_SECRET
          valueFrom:
            secretKeyRef:
              name: wygiwyh-secrets
              key: oauth-client-secret
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
- If `WYGIWYH_MCP_API_AUTH_MODE=incoming_bearer`, verify `WYGIWYH` exposes OAuth metadata and the introspection client credentials are correct

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
