# VPS Deployment

Docker Compose deployment for a VPS already running Caddy as a reverse proxy.

## Architecture

```
docker-compose.prod.yml
├── inf3-api        uvicorn :8001     (shared Python image)
├── inf3-worker     inf3-worker       (same image, polls queue)
└── inf3-frontend   Next.js :3000     (standalone build)

Existing Caddy (separate compose, shared "web" network)
├── inspect.lakesideai.dev/api*  → inf3-api:8001
└── inspect.lakesideai.dev/*     → inf3-frontend:3000
```

All three services share a `inf3-data` volume mounted at `/data` for the file-based queue and outputs. The API and worker both set `working_dir: /data` so relative paths (`.inf3-analytics/queue/`) resolve to the same location.

## Prerequisites

- Docker + Docker Compose v2
- An external Docker network named `web` (shared with Caddy)
- Caddy running in its own compose on the same `web` network

Create the external network if it doesn't exist:

```bash
docker network create web
```

## Setup

### 1. Clone and configure

```bash
cd /opt  # or wherever you keep projects
git clone <repo-url> inf-3-analytics
cd inf-3-analytics
```

Copy the env template and fill in your API keys:

```bash
cp deploy/.env.example .env
$EDITOR .env
```

The `.env` file only needs secrets and tuning knobs — data paths are set in `docker-compose.prod.yml` via the `environment` block.

### 2. Add Caddyfile entry

Add this block to your VPS Caddyfile (wherever your Caddy compose manages it):

```caddyfile
inspect.lakesideai.dev {
  handle_path /api* {
    reverse_proxy inf3-api:8001 {
      flush_interval -1
    }
  }
  handle {
    reverse_proxy inf3-frontend:3000
  }
}
```

`flush_interval -1` disables response buffering, required for SSE streams from the API.

Then reload Caddy:

```bash
docker compose -f /path/to/caddy/docker-compose.yml restart caddy
```

### 3. Build and start

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 4. Verify

```bash
# All 3 services running, API healthy
docker compose -f docker-compose.prod.yml ps

# Health check
curl http://localhost:8001/health
# → {"status":"ok"}

# Through Caddy (after DNS propagates)
curl https://inspect.lakesideai.dev/api/health
curl https://inspect.lakesideai.dev/api/runs
```

## Operations

### Logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Single service
docker compose -f docker-compose.prod.yml logs -f inf3-worker
```

### Redeploy after code changes

```bash
cd /opt/inf-3-analytics
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

### Restart a single service

```bash
docker compose -f docker-compose.prod.yml restart inf3-worker
```

### Data volume

The `inf3-data` named volume persists uploads, outputs, and the run registry across container restarts. To inspect it:

```bash
docker volume inspect inf-3-analytics_inf3-data
```

To back up:

```bash
docker run --rm -v inf-3-analytics_inf3-data:/data -v $(pwd):/backup alpine \
  tar czf /backup/inf3-data-backup.tar.gz -C /data .
```

## Networking

| Network    | Purpose                                  | Services                    |
|------------|------------------------------------------|-----------------------------|
| `web`      | External — Caddy routes traffic in       | inf3-api, inf3-frontend     |
| `internal` | Bridge — API ↔ worker communication only | inf3-api, inf3-worker       |

The worker is not on `web` — it's only reachable by the API over `internal`.

## Local development

The Docker setup is for VPS deployment only. For local development / tunnel demos, use:

```bash
BASIC_AUTH_PASS=yourpassword bash scripts/start-demo.sh
```

This runs bare processes (uvicorn, worker, Next.js dev server, Caddy, optional Cloudflare tunnel) without Docker.
