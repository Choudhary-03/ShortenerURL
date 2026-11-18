# Deployment Guide (Docker)

The stack runs as containers: `web` (Gunicorn), `worker` (Celery), `db` (PostgreSQL 16), `redis`, and optionally `caddy` (reverse proxy with automatic HTTPS).

```
Internet ──► caddy :80/:443 ──► web :8000 ──► db (PostgreSQL)
                                  │   └────► redis (cache)
                                  └─ queues ─► redis ─► worker ──► db
```

All commands run from the project root. Compose is invoked as:

```
docker compose -f deployment/docker-compose.yml --env-file .env <command>
```

Below this is shortened to `dc`. On Linux/macOS: `alias dc='docker compose -f deployment/docker-compose.yml --env-file .env'`. In PowerShell: `function dc { docker compose -f deployment/docker-compose.yml --env-file .env @args }`.

## 1. Prerequisites

- Docker Engine with Compose v2 (`docker compose version`). On Windows or macOS, Docker Desktop.
- For a public server: a Linux VPS, ports 80 and 443 open, and a domain with an A record pointing at the server's IP.

## 2. Create the `.env` file

```bash
cp .env.example .env          # PowerShell: Copy-Item .env.example .env
```

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

**Local test** (`.env`):

```
SECRET_KEY=<generated value>
POSTGRES_PASSWORD=<a strong password>
```

**Production** (`.env`):

```
SECRET_KEY=<generated value>
POSTGRES_PASSWORD=<a strong password>
DOMAIN=short.example.com
ALLOWED_HOSTS=short.example.com
BASE_SHORT_URL=https://short.example.com
CSRF_TRUSTED_ORIGINS=https://short.example.com
WEB_BIND=127.0.0.1:8000
HTTPS_ENABLED=True
ANALYTICS_TRUST_PROXY=True
```

`SECRET_KEY` and `POSTGRES_PASSWORD` are required; compose refuses to start without them. Never commit `.env`.

## 3. Generate migrations (once)

The image needs migration files, and the `web` container refuses to start without them. If you have Python and the venv locally:

```bash
python manage.py makemigrations accounts shortener analytics
```

Without local Python, generate them inside a container (PowerShell shown; use `$(pwd)` on Linux/macOS):

```powershell
dc build web
dc run --rm --no-deps --user root -e RUN_MIGRATIONS=0 -v "${PWD}:/app" web python manage.py makemigrations accounts shortener analytics
```

A warning that the database host `db` could not be reached is harmless here. Commit the generated `migrations/0001_initial.py` files, then rebuild (`dc build`). On Linux, the generated files are owned by root; fix with `sudo chown -R $USER .`.

## 4. Start

**Local test (HTTP on port 8000):**

```bash
dc up --build
```

Open `http://localhost:8000/api/docs/`.

**Production (HTTPS through Caddy):**

```bash
dc --profile proxy up -d --build
```

Caddy requests a Let's Encrypt certificate for `DOMAIN` on first start (DNS must already point at the server). Open `https://short.example.com/api/docs/`. To test the proxy locally, set `DOMAIN=localhost` and accept the self-signed certificate warning.

## 5. Create an admin user

```bash
dc exec web python manage.py createsuperuser
```

## 6. Check that it works

```bash
dc ps                          # web should show "healthy"
dc logs -f web worker          # follow logs (Ctrl+C to stop)
```

Then register a user, create a link, open it, and read its analytics (see the PowerShell examples in `api_documentation.md`). A click only appears if the `worker` container is running.

## Updating to a new version

```bash
git pull
dc --profile proxy up -d --build
```

Migrations are applied automatically when `web` starts. If you changed models, run `makemigrations` first and commit the files, or the container will stop with an explanatory error.

## Backups and restore

Back up (run on the server; the script uses `sh`):

```bash
sh scripts/backup_db.sh        # writes backups/shortener_<timestamp>.sql.gz
```

Restore into the running database:

```bash
gunzip -c backups/shortener_20261106_101500.sql.gz | dc exec -T db sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'
```

Schedule backups with cron, for example daily at 02:00:

```
0 2 * * * cd /path/to/url_shortener && sh scripts/backup_db.sh
```

Copy backups off the server regularly. Redis holds only cache and queued tasks, so it needs no backup.

## Scaling and tuning

- More click-processing capacity: `dc up -d --scale worker=3`.
- More web capacity: raise `--workers` in the `web` command in `docker-compose.yml` (a common starting point is 2 x CPU cores + 1).
- Clicks accumulate in the `clicks` table; plan retention or archiving as described in `database_design.md`.

## Stopping and cleaning up

```bash
dc down                        # stop containers, keep data
dc down -v                     # stop and DELETE all data (database, redis, certificates)
```

## Security checklist

- Strong, unique `SECRET_KEY` and `POSTGRES_PASSWORD`; `.env` not in git.
- `DEBUG` is always `False` in containers.
- `WEB_BIND=127.0.0.1:8000` so the app is reachable only through Caddy. The database and Redis publish no ports at all.
- Firewall: allow only 22 (SSH), 80, and 443.
- `HTTPS_ENABLED=True` turns on secure cookies and HSTS (30 days).
- `ANALYTICS_TRUST_PROXY=True` only when traffic really goes through Caddy; otherwise clients can spoof their IP.
- Throttle `register` and `login` before opening the service to the public.
- Restrict `/admin/` and `/api/docs/` (for example by IP in the Caddyfile) if they should not be public.
- Keep images updated: `dc pull && dc up -d --build`.

## Troubleshooting

| Symptom | Likely cause and fix |
|---------|----------------------|
| `Set SECRET_KEY in .env` | The variable is missing, or you forgot `--env-file .env` |
| `web` exits with "models have no matching migration files" | Generate and commit migrations (step 3), then rebuild |
| `web` stays "unhealthy" | `dc logs web`. Often a wrong `ALLOWED_HOSTS` or a database connection error |
| `400 Bad Request` in the browser | The domain is not in `ALLOWED_HOSTS` |
| Admin login: CSRF verification failed | Add `https://your-domain` to `CSRF_TRUSTED_ORIGINS` |
| Clicks never show up in analytics | The `worker` is not running (`dc ps`), or the broker URL is wrong |
| Caddy cannot get a certificate | DNS does not point at the server yet, or ports 80/443 are blocked |
| `exec ./entrypoint.sh: no such file or directory` | Windows line endings in `entrypoint.sh`; `.gitattributes` and the Dockerfile fix this, so rebuild with `--no-cache` |
| Port 8000 already in use | Stop the local dev server, or change `WEB_BIND` |
