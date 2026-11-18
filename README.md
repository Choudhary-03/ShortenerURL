# URL Shortener

A Django REST API for creating short links, redirecting visitors, and tracking click analytics. It uses a service/selector architecture, JWT authentication, Redis caching, and Celery for background click recording.

## Status

| Component | Status |
|-----------|--------|
| Accounts: register, login, profile, change password | Implemented |
| Shortener: create, list, update, delete, redirect | Implemented |
| Analytics: click tracking, summary, time series | Implemented |
| Swagger / ReDoc API docs (drf-spectacular) | Implemented |
| Monitoring: health and metrics | Planned |
| Settings split, Docker deployment | Planned |

## Features

- Email-based user accounts with JWT access and refresh tokens
- Random base62 short codes (not guessable) or custom aliases
- Optional link expiry, and activate/deactivate without deleting
- Fast redirects: Redis cache first, database on a miss
- Asynchronous click recording through Celery, so redirects are never slowed down
- Per-link analytics: totals, devices, browsers, countries, referrers, and time series
- IP anonymization by default
- Interactive API documentation at `/api/docs/`

## Tech Stack

Python 3.11+, Django, Django REST Framework, simplejwt, drf-spectacular, Celery, Redis, user-agents, PostgreSQL (SQLite works for local development).

## Quick Start

All commands are run from the folder containing `manage.py`.

### 1. Environment

```powershell
# Windows PowerShell
python -m venv venv
venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 2. Install

```bash
pip install django djangorestframework djangorestframework-simplejwt drf-spectacular celery redis user-agents
```

(When you have `requirements/development.txt`, use `pip install -r requirements/development.txt` instead.)

### 3. Migrate and create an admin

```bash
python manage.py makemigrations accounts shortener analytics
python manage.py migrate
python manage.py createsuperuser
```

`AUTH_USER_MODEL = "accounts.User"` must be set before the first `migrate`. If you migrated earlier with Django's default user model, delete the dev database and migration files and start again.

`createsuperuser` asks for email, and for full name if `REQUIRED_FIELDS = ["full_name"]` is set on the `User` model.

### 4. Run

Without Redis, run Celery tasks inline:

```powershell
$env:CELERY_EAGER = "True"; python manage.py runserver
```

```bash
CELERY_EAGER=True python manage.py runserver
```

With Redis, run the server and a worker (two terminals):

```bash
python manage.py runserver
celery -A config worker -l info          # on Windows add: -P solo
```

The API is at `http://127.0.0.1:8000/api/v1/` and the interactive docs at `http://127.0.0.1:8000/api/docs/`.

## Configuration

Read from environment variables by the current code:

| Variable | Default | Purpose |
|----------|---------|---------|
| `BASE_SHORT_URL` | `http://127.0.0.1:8000` | Public base used to build `short_url` |
| `REDIS_URL` | unset | Cache backend. If unset, an in-memory cache is used |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery broker |
| `CELERY_EAGER` | `False` | `True` runs tasks inline (development without Redis) |

Constants in `settings.py`:

| Setting | Default | Purpose |
|---------|---------|---------|
| `SHORT_CODE_LENGTH` | `7` | Length of generated codes |
| `SHORT_URL_CACHE_TTL` | `3600` | Seconds a redirect stays cached |
| `ANALYTICS_ANONYMIZE_IP` | `True` | Store IPs truncated to /24 (IPv4) or /48 (IPv6) |
| `ANALYTICS_TRUST_PROXY` | `False` | Trust `X-Forwarded-For` (only behind a proxy you control) |

`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, and `DATABASE_URL` should move to environment variables when you split settings into dev and prod. Never commit `.env`.

## API Overview

Base path: `/api/v1/`. Full details are in [docs/api_documentation.md](docs/api_documentation.md).

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register/` | No | Create an account |
| POST | `/auth/login/` | No | Get access and refresh tokens |
| POST | `/auth/token/refresh/` | No | Refresh an access token |
| GET, PUT, PATCH | `/auth/me/` | Yes | View or update profile |
| POST | `/auth/change-password/` | Yes | Change password |
| POST, GET | `/urls/` | Yes | Create or list your short URLs |
| GET, PUT, PATCH, DELETE | `/urls/{id}/` | Yes (owner) | Manage one short URL |
| GET | `/urls/{id}/analytics/` | Yes (owner) | Click totals and breakdowns |
| GET | `/urls/{id}/analytics/timeseries/` | Yes (owner) | Clicks over time |
| GET | `/{short_code}` | No | Redirect (302) |

Interactive documentation: `/api/docs/` (Swagger UI), `/api/redoc/` (ReDoc), `/api/schema/` (OpenAPI schema).

## Project Structure

```
url_shortener/
├── config/        Settings, root URLs, Celery app
├── accounts/      Custom user model, auth, profile
├── shortener/     Short URLs, validation, caching, redirect
├── analytics/     Click events, Celery task, statistics
├── common/        Shared helpers (planned use)
├── monitoring/    Health and metrics (planned)
├── tests/         Integration and performance tests
├── docs/          Architecture, API, and database docs
├── requirements/  base / development / production
└── deployment/    Dockerfile, docker-compose, entrypoint
```

## Testing

```bash
python manage.py test accounts
python manage.py test analytics
python manage.py test            # everything
```

Shortener tests (services, validators, redirect caching) are still to be written.

## Documentation

- [Architecture](docs/architecture.md)
- [API Documentation](docs/api_documentation.md)
- [Database Design](docs/database_design.md)

## Conventions

- Business logic lives in `services.py`; views stay thin.
- Read queries live in `selectors.py`.
- Serializers validate input shape only, not business rules.
- Routes are versioned under `/api/v1/`; the redirect pattern is the last entry in `config/urls.py`.

## Roadmap

1. ~~Accounts~~
2. ~~Shortener~~
3. ~~Analytics~~
4. Tests for shortener
5. Monitoring: `/health/` and `/metrics/`
6. Settings split (base, development, production)
7. Docker deployment
