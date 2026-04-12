# Django Skills Registry

## Quick Start

1. Install dependencies with uv from repository root.

```bash
uv sync
```

2. Run migrations.

```bash
uv run python django_registry/manage.py makemigrations
uv run python django_registry/manage.py migrate
```

3. Start service.

```bash
uv run python django_registry/manage.py runserver 0.0.0.0:8001
```

4. (Optional) Add more dependencies using uv.

```bash
uv add <package-name>
```

## Main API

- `GET /api/v1/skills/resolve?owner_id=<id>&skill_name=<name>`
- `GET /api/v1/skills/common/`
- `POST /api/v1/distribution/issue-download-token`
- `POST /api/v1/distribution/resolve-download-token`

## Notes

- By default, SQLite is used.
- Set `REGISTRY_DB_ENGINE=postgres` and related DB env vars to use PostgreSQL.
