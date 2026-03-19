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

### 2. Set up Basic Auth

Generate a bcrypt hash for your password:

```bash
docker run --rm caddy:2-alpine caddy hash-password --plaintext 'YOUR_PASSWORD'
```

Add the hash to your `.env`:

```
BASIC_AUTH_USER=tester
BASIC_AUTH_HASH=$2a$14$...the hash output...
```

### 3. Add Caddyfile entry

Add this block to your VPS Caddyfile (wherever your Caddy compose manages it):

```caddyfile
inspect.lakesideai.dev {
  basic_auth {
    {$BASIC_AUTH_USER} {$BASIC_AUTH_HASH}
  }

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

Make sure the Caddy compose loads the `.env` file:

```yaml
env_file:
  - ../inf3/inf-3-analytics/.env
```

Then reload Caddy:

```bash
docker compose -f /path/to/caddy/docker-compose.yml restart caddy
```

### 4. Build and start

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 5. Verify

```bash
# All 3 services running, API healthy
docker compose -f docker-compose.prod.yml ps

# Through Caddy (requires Basic Auth)
curl -u tester https://inspect.lakesideai.dev/api/health
# → {"status":"ok"}

curl -u tester https://inspect.lakesideai.dev/api/runs
# → {"runs":[]}

# Unauthenticated requests should get 401
curl -s -o /dev/null -w "%{http_code}" https://inspect.lakesideai.dev/api/health
# → 401
```

Note: the API is not exposed to the host — it's only reachable through Caddy on the `web` Docker network.

### 6. Connect

Open https://inspect.lakesideai.dev in a browser. You'll be prompted for Basic Auth credentials (`tester` / your password). The frontend talks to the API at `/api`.

## Operations

### Logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Single service
docker compose -f docker-compose.prod.yml logs -f inf3-worker
```

### Stop / tear down

```bash
# Stop all services (keeps volumes)
docker compose -f docker-compose.prod.yml down

# Stop and delete data volume too
docker compose -f docker-compose.prod.yml down -v
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
