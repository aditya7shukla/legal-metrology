# Deployment Guide

## Option A — Docker Compose (single server / pilot deployment)

Suitable for a departmental pilot on a single VM (e.g. an NIC/state data
centre VM, or any cloud VM with Docker installed).

```bash
git clone <this-repo>
cd lmcs
cp .env.example .env
```

Edit `.env`:
```
POSTGRES_PASSWORD=<generate a strong password>
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(64))">
```

```bash
docker compose up --build -d
docker compose ps            # confirm db, backend, frontend are healthy
```

**Create the first admin account** (one-time; the endpoint disables itself
after this):
```bash
curl -X POST http://localhost:8000/api/v1/auth/bootstrap-admin \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Director, Legal Metrology",
    "email": "admin@yourdept.gov.in",
    "password": "<a strong password>",
    "designation": "Director"
  }'
```

Then log in at `http://<server-ip>/` and use **Settings → (future) User
Management** or `POST /api/v1/auth/register` (as admin) to create officer
accounts.

**Database migrations**: the app auto-creates tables on first boot for
convenience. For any subsequent schema change, use Alembic instead of
relying on auto-create:
```bash
docker compose exec backend alembic revision --autogenerate -m "describe change"
docker compose exec backend alembic upgrade head
```

## Option B — Managed cloud services (recommended for state-wide rollout)

| Component | Suggested service |
|---|---|
| Backend (FastAPI container) | AWS ECS/Fargate, Azure Container Apps, GCP Cloud Run, or NIC Cloud (MeghRaj) container hosting |
| Database | AWS RDS for PostgreSQL / Azure Database for PostgreSQL / managed Postgres on MeghRaj |
| File storage | S3 / Azure Blob / GCS (see `docs/ARCHITECTURE.md` "Object storage") instead of local volumes |
| Frontend | Static hosting (S3+CloudFront, Azure Static Web Apps) or the same container behind a CDN |
| Task queue (at scale) | Managed Redis + Celery workers, or SQS/Cloud Tasks |
| Secrets | AWS Secrets Manager / Azure Key Vault — never commit `.env` |
| TLS | ACM/managed certificates behind an ALB, or Let's Encrypt via Nginx/Caddy |

## Production checklist

- [ ] `SECRET_KEY` is a long random value, stored in a secrets manager, not in source control.
- [ ] `DATABASE_URL` points to a managed/backed-up PostgreSQL instance, not the SQLite default.
- [ ] HTTPS is enforced end-to-end (browser ↔ frontend ↔ backend).
- [ ] `CORS_ORIGINS` is restricted to your actual frontend domain(s) — no wildcard.
- [ ] Default seed accounts (`scripts/seed.py`) are **not** used in production; the bootstrap-admin flow is used instead and the endpoint is confirmed disabled afterward (it self-disables once any user exists).
- [ ] File storage (uploads + generated reports) is backed by durable, backed-up storage (managed volume or object storage), not an ephemeral container filesystem.
- [ ] Database backups are scheduled (point-in-time recovery recommended given evidentiary use).
- [ ] `backend/app/rules/*.json` has been reviewed and signed off by a Legal Metrology / legal officer against the current Gazette-notified Rules (see the `_meta.disclaimer` field in each file).
- [ ] Log retention/monitoring is configured (the `audit_logs` table plus your platform's container logs).
- [ ] A vulnerability scan and dependency audit (`pip-audit`, `npm audit`) has been run before go-live, and periodically thereafter.
- [ ] Role assignment reviewed: only trusted staff hold `admin`; field officers use `officer`; external/read-only stakeholders use `viewer`.
- [ ] Rate limiting / WAF is placed in front of publicly reachable endpoints if this will be internet-facing rather than on a government intranet.

## Environment variables reference

See `backend/.env.example` for the full list. Key ones:

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | JWT signing secret | **must be overridden** |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///./lmcs.db` (dev only) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token lifetime | 480 (8h) |
| `TESSERACT_CMD` | Path to tesseract binary if not on PATH | auto-detect |
| `OCR_LANGUAGES` | Tesseract language codes, e.g. `eng+hin` | `eng` |
| `CORS_ORIGINS` | Allowed frontend origins (JSON array) | localhost dev ports |
| `MAX_UPLOAD_SIZE_MB` | Upload size cap | 15 |

## Rolling back / disaster recovery

- Database: restore from the most recent PostgreSQL backup/snapshot.
- File storage: if using object storage with versioning enabled, restore
  affected objects; if using a Docker volume, restore from your volume
  backup schedule.
- Application: containers are stateless — redeploying the previous image tag
  is sufficient; no special migration-down process is required unless a
  schema migration also needs reverting (`alembic downgrade -1`).
