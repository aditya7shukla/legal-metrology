# Architecture

## System overview

```
                    ┌──────────────────────────┐
                    │        Frontend           │
                    │  React (Vite) SPA served  │
                    │  via Nginx                │
                    │  - Login / RBAC-aware nav │
                    │  - Scan upload            │
                    │  - Repository & search    │
                    │  - Reports & review       │
                    │  - Dashboard (Recharts)   │
                    └────────────┬──────────────┘
                                 │ REST (JSON) over HTTPS
                                 ▼
                    ┌──────────────────────────┐
                    │      Backend (FastAPI)    │
                    │  ┌────────────────────┐  │
                    │  │ Routers             │  │
                    │  │ auth / products /   │  │
                    │  │ scans / reports /    │  │
                    │  │ dashboard            │  │
                    │  └─────────┬───────────┘  │
                    │            ▼               │
                    │  ┌────────────────────┐   │
                    │  │ Services            │   │
                    │  │ - image_preprocess  │   │
                    │  │ - ocr_service        │   │
                    │  │ - rule_engine        │   │
                    │  │ - report_generator   │   │
                    │  └─────────┬───────────┘   │
                    │            ▼               │
                    │  ┌────────────────────┐   │
                    │  │ SQLAlchemy models    │   │
                    │  └─────────┬───────────┘   │
                    └────────────┼───────────────┘
                                 ▼
                    ┌──────────────────────────┐
                    │  PostgreSQL (production)  │
                    │  SQLite (local dev only)  │
                    └──────────────────────────┘

           File storage: /storage/uploads (images), /storage/reports (PDF/DOCX)
           — a Docker named volume locally; swap for S3/Azure Blob/GCS in production
           (see "Object storage" below).
```

## Request flow: a single scan

1. Officer uploads an image + product metadata via `POST /api/v1/scans`
   (multipart form).
2. `utils/file_storage.py` validates file type/size and saves the original +
   a thumbnail to disk.
3. `services/image_preprocessing.py` deskews, corrects illumination, denoises,
   and binarizes the image for OCR.
4. `services/ocr_service.py` runs Tesseract (`image_to_data`) to get word-level
   text with bounding boxes and confidence, groups words into lines, and
   estimates each line's printed height in millimetres.
5. `services/rule_engine.py` evaluates the extracted full text + font
   measurements against `app/rules/declarations_rules.json` and
   `font_size_rules.json`, producing a score, status, and itemized violations.
6. `services/report_generator.py` renders the result to PDF and DOCX.
7. Everything is persisted (`ScanRecord`, `ComplianceReport`,
   `ViolationDetail`) and an `AuditLog` entry is written.
8. The scan response (including `report_id`) is returned to the frontend,
   which immediately shows the result and links to the full report.

This is currently a **synchronous** request/response flow for simplicity of
deployment. See "Scaling the pipeline" below for the production alternative.

## Data model

| Table | Purpose |
|---|---|
| `users` | Officers/admins/viewers. Role-based access control (`admin`, `officer`, `viewer`). |
| `products` | The repository: one row per distinct product/SKU, reused across scans. |
| `scan_records` | One row per uploaded image + its OCR/extraction output. |
| `compliance_reports` | One row per scan's evaluation result — score, status, generated file paths, review/finalize state. |
| `violation_details` | One row per individual finding on a report (declaration, severity, description). |
| `audit_logs` | Append-only trail of logins, scan completions, and report reviews, for enforcement accountability. |

## Why the rule logic lives in JSON, not code

`backend/app/rules/declarations_rules.json` and `font_size_rules.json` are the
single source of truth for *what counts as a violation*. This is a deliberate
separation:

- A Legal Metrology / legal compliance officer can review, correct, or
  extend the rule set (add a new declaration, adjust a font-size threshold,
  change severity) **without a code change or redeploy**.
- `services/rule_engine.py` is a generic evaluator over that config — it has
  no hardcoded knowledge of "MRP" or "net quantity" wording.
- Every rule entry carries its `rule_ref` (e.g. `Rule 6(1)(f)`) so violations
  are traceable back to the specific legal provision.

See `docs/LEGAL_METROLOGY_RULES_MAPPING.md` for the full mapping and its
documented limitations.

## Security

- Passwords hashed with bcrypt (via passlib).
- JWT access tokens (8h default) + refresh tokens (7d default), configurable.
- Role-based access control (`require_roles()` dependency) on every
  write endpoint; viewers get read-only access.
- Audit logging on login, scan completion, and report review actions.
- File upload validation: extension allow-list + size cap.
- CORS is explicitly configured (no wildcard in production config).
- **Before go-live**: put the stack behind HTTPS (terminate TLS at a load
  balancer or Nginx with a real certificate — the shipped `nginx.conf` is
  HTTP-only for local/demo use), rotate `SECRET_KEY`, and review
  `docs/DEPLOYMENT.md`'s production checklist.

## Known limitations (by design, documented rather than hidden)

1. **OCR accuracy on real-world photos.** Glare, skew, low resolution, or
   non-English text (`OCR_LANGUAGES` can be extended, e.g. `eng+hin`) reduce
   extraction accuracy. The system is a *pre-screening* aid; every
   "non-compliant" finding should be visually verified by the officer before
   any action is taken. The review/finalize workflow on each report exists
   specifically for this.
2. **Font-size-in-mm is an estimate unless calibrated.** See
   `ocr_service.py`'s module docstring — pixel-to-mm conversion needs a known
   physical scale (a reference card in frame, or true capture DPI). Absent
   that, the system falls back to an assumed DPI and marks the measurement
   `"estimated"` rather than presenting a false-precision number.
3. **"Generic name of commodity" (Rule 6(1)(b)) has no fixed text pattern**,
   so it's currently always flagged for manual confirmation rather than
   auto-detected/rejected — see the `presence_heuristic` detection type in
   `rule_engine.py`. This avoids a worse failure mode (false "missing"
   flags on every scan).
4. **Multiple-MRP detection is a heuristic**, not a definitive violation —
   it commonly fires on legitimate "was/now" reduced-price stickers and is
   deliberately scored as `minor`/advisory pending officer review.
5. **Single synchronous worker per request.** Fine for departmental pilot
   volumes; see "Scaling the pipeline" for high-volume production.

## Scaling the pipeline

For high scan volumes (state-wide rollout, e-commerce crawler ingestion),
replace the synchronous body of `POST /api/v1/scans` with:

1. Endpoint saves the upload, creates a `ScanRecord` with `status=queued`,
   and enqueues a job (Celery + Redis/RabbitMQ, or a managed queue like AWS
   SQS / GCP Cloud Tasks) referencing the `scan_id`.
2. A pool of worker processes runs `ocr_service` → `rule_engine` →
   `report_generator` (the same service functions used today — no rewrite
   needed) and updates the `ScanRecord`/`ComplianceReport` on completion.
3. Frontend polls `GET /api/v1/scans/{id}` (or subscribes via WebSocket/SSE)
   until `status=completed`.
4. Horizontally scale OCR workers independently of the API — OCR is the CPU-
   heavy step.

## Object storage for production

Swap `UPLOAD_DIR`/`REPORT_DIR` local paths for an S3-compatible bucket
(AWS S3, GCS, Azure Blob, or MinIO for on-prem/air-gapped deployments):
wrap `utils/file_storage.py`'s save/read calls behind a small storage
interface (`save(file) -> url`, `read(url) -> bytes`) so the rest of the
codebase doesn't need to change. Serve images via signed URLs rather than
the current `/media` static mount once you're off local disk.

## E-commerce listing ingestion (future extension)

The data model already supports `listing_type=ecommerce_listing` and a
Rule 6(10)-specific composite check. A production rollout targeting online
marketplaces would add a scheduled crawler/API-integration service that
screenshots product listing pages and submits them through the same
`POST /api/v1/scans` endpoint — no core pipeline changes required.
