# Reverse Proxy Stack

Shared Traefik ingress for hosting multiple Dockerized apps on one server.

## Start

```bash
cp .env.example .env
docker compose up -d
```

Traefik binds host ports `80` and `443` and auto-discovers app routes from Docker labels.

## Dashboard (optional)

Dashboard route defaults to `traefik.local` (set by `TRAEFIK_DASHBOARD_HOST`).
Map that hostname to your server IP in DNS or `/etc/hosts`.
