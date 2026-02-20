# Meal Planner

A web application for recipe management, weekly meal planning, and grocery list generation.

## Features

- **Recipe Scraping**: Import recipes from Ambitious Kitchen and Smitten Kitchen
- **Recipe Box**: Save your favorite recipes
- **Weekly Planner**: Assign recipes to days of the week
- **Smart Grocery List**: Automatically aggregates ingredients across recipes

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, SQLite
- **Frontend**: React, TypeScript, Vite, Tailwind CSS
- **Recipe Scraping**: BeautifulSoup for JSON-LD extraction

## Prerequisites

- [uv](https://docs.astral.sh/uv/) for Python dependency and virtualenv management.
  Backend target runtime: Python `3.14`.
  Install directly:
  - macOS/Linux:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
  - Windows (PowerShell):
    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```
- Node.js + npm for frontend development
- Docker + Docker Compose (for container deployment)

## Getting Started

### Quick Start (Recommended)

```bash
# Run everything with one command
./run.sh
```

This will:
- Install Python and Node dependencies (first run only)
- Start both backend and frontend servers

Then open http://localhost:5173

### Other Commands

```bash
./run.sh setup      # Install dependencies only
./run.sh backend    # Start only the backend
./run.sh frontend   # Start only the frontend
```

### Manual Setup

If you prefer to run things manually:

**Backend:**
```bash
cd backend
uv sync --group dev
uv run uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Backend quality checks:**
```bash
cd backend
uv run ruff check .
uv run ruff format .
uv run ty check
uv run pytest
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Docker Deployment (Multi-App / LAN)

This repository is configured for a shared reverse proxy so multiple apps can coexist on one server without port conflicts.

One-time server setup (shared across all apps):
```bash
cd infra/reverse-proxy
docker compose up -d
```

App deployment:
```bash
# In repo root
cp .env.example .env
# Set APP_HOST to your shared proxy hostname (example: kittenserver-1.taild4e01a.ts.net)
# Set APP_PATH_PREFIX to this app's unique path (example: /meals)
# Optional: set OPENAI_API_KEY to enable LLM normalization

docker compose up -d --build
docker compose ps
```

How routing works:
- Traefik listens on server ports `80` and `443`.
- Meal Planner does not bind host ports; it is routed by host + path (`APP_HOST` + `APP_PATH_PREFIX`).
- Nginx inside the frontend container still proxies `/api/*` to the backend service.

Open the app at `http://<APP_HOST><APP_PATH_PREFIX>` (example: `http://kittenserver-1.taild4e01a.ts.net/meals`).

#### Current Production Setup (kittenserver + Tailscale)

Current values on the server:
- `APP_HOST=kittenserver-1.taild4e01a.ts.net`
- `APP_PATH_PREFIX=/meals`
- App URL: `http://kittenserver-1.taild4e01a.ts.net/meals`

Server directories:
- Reverse proxy stack: `~/infra/reverse-proxy`
- Meal Planner app stack: `~/apps/meal-planner`

Bring up / update proxy:
```bash
cd ~/infra/reverse-proxy
cp .env.example .env   # first time only
docker compose up -d
```

Bring up / update Meal Planner:
```bash
cd ~/apps/meal-planner
cp .env.example .env   # first time only
# set APP_HOST and APP_PATH_PREFIX in .env
docker compose up -d --build
```

#### GitHub Actions Deployment (kittenserver)

This repo includes `.github/workflows/deploy-kittenserver.yml` to deploy over SSH with `rsync` + `docker compose`.

Required repository variables:
- `DEPLOY_HOST` (example: `kittenserver` or `kittenserver-1.taild4e01a.ts.net`)

Optional repository variables:
- `DEPLOY_USER` (default: `saiaj`)
- `DEPLOY_PATH` (default: `/home/saiaj/apps/meal-planner`)

Required repository secrets:
- `DEPLOY_SSH_KEY` (private key for SSH auth)

Optional repository secrets:
- `DEPLOY_SSH_KNOWN_HOSTS` (recommended pinned host key line from `ssh-keyscan -H <host>`)
- `TS_AUTHKEY` (only needed if the runner must join your Tailscale tailnet to reach the server)

Run it from the Actions tab using **Deploy to kittenserver** (`workflow_dispatch` trigger).

Verify deployment:
```bash
curl -i -H 'Host: kittenserver-1.taild4e01a.ts.net' http://127.0.0.1/meals/
curl -sS -H 'Host: kittenserver-1.taild4e01a.ts.net' http://127.0.0.1/meals/api/recipes
```

Notes:
- `http://<APP_HOST>/` returning `404` is expected when path-based routing is enabled.
- The app is intentionally served at `/meals` so other apps can use different prefixes (for example `/notes`, `/wiki`).
- With Tailscale MagicDNS, clients on the tailnet can open the app directly using the Tailscale hostname.

#### Adding Another App Behind The Same Traefik

For each additional app:
1. Reuse the same `APP_HOST`.
2. Choose a unique `APP_PATH_PREFIX` (for example `/notes`).
3. Ensure that app’s frontend build base is set to that prefix.
4. Deploy with labels that match `Host(APP_HOST) && PathPrefix(APP_PATH_PREFIX)`.

## Supported Recipe Sites

- [Ambitious Kitchen](https://www.ambitiouskitchen.com/)
- [Smitten Kitchen](https://smittenkitchen.com/)

Other sites may work if they include JSON-LD structured recipe data.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/recipes/scrape` | POST | Scrape recipe from URL |
| `/api/recipes` | GET | List all saved recipes |
| `/api/recipes/{id}` | GET/DELETE | Get or delete recipe |
| `/api/recipes/{id}/add-to-box` | POST | Add to recipe box |
| `/api/recipes/box/all` | GET | Get recipe box contents |
| `/api/meal-plans` | GET/POST | Manage weekly meal plans |
| `/api/grocery-list` | POST | Generate aggregated grocery list |

## Project Structure

```
hack_day_project/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI entry point
│   │   ├── database.py       # SQLAlchemy setup
│   │   ├── models.py         # Database models
│   │   ├── routers/          # API endpoints
│   │   └── services/         # Business logic
│   ├── pyproject.toml        # Python deps + ruff/pytest config
│   └── uv.lock               # Locked dependency graph for uv
├── frontend/
│   └── src/
│       ├── components/       # React components
│       └── api/              # API client
└── README.md
```
