# Legal Metrology Compliance Checking System

An automated software system for scanning packaged-commodity labels, product
images and e-commerce listings to screen for compliance with the
**Legal Metrology (Packaged Commodities) Rules, 2011** (India).

Built for Legal Metrology / Consumer Affairs enforcement teams to speed up
routine label inspection, standardize findings, and maintain a searchable
compliance history — while keeping a human officer firmly in the loop for
every final determination.

---

## What it does

1. **Scan** — an officer photographs a product label (or uploads an
   e-commerce listing screenshot) via the web app.
2. **Extract** — the backend runs OpenCV preprocessing + Tesseract OCR to
   pull text and measure font sizes.
3. **Evaluate** — a rule engine checks the extracted text against Rule 6
   mandatory declarations (manufacturer details, net quantity, MRP, date of
   manufacture, consumer care, country of origin, etc.), font-size minimums,
   and common prohibited practices.
4. **Report** — a compliance report (score + itemized violations) is
   generated instantly, downloadable as PDF (fixed/evidentiary) or DOCX
   (editable, for officer annotation).
5. **Track** — every product and scan is kept in a searchable repository with
   full inspection history, and a dashboard rolls up trends for supervisors.

## Project layout

```
lmcs/
├── backend/          FastAPI application (Python) — OCR, rule engine, reports, API
│   ├── app/
│   │   ├── rules/    Editable JSON: mandatory-declaration & font-size rule tables
│   │   ├── routers/  REST endpoints (auth, products, scans, reports, dashboard)
│   │   ├── services/ OCR pipeline, rule engine, PDF/DOCX report generator
│   │   └── models.py SQLAlchemy schema
│   ├── alembic/      DB migrations
│   ├── tests/        Unit tests for the rule engine
│   └── scripts/seed.py
├── frontend/         React (Vite) single-page app — officer-facing UI
│   └── src/
│       ├── pages/    Login, Dashboard, Scan Upload, Repository, Reports
│       └── components/
├── docs/             Architecture, deployment, API and legal-rule mapping docs
└── docker-compose.yml
```

## Quick start (Docker — recommended)

```bash
cp .env.example .env                  # set SECRET_KEY and POSTGRES_PASSWORD
docker compose up --build
```

- Frontend: http://localhost
- Backend API docs (Swagger): http://localhost:8000/api/docs
- First-time setup: call `POST /api/v1/auth/bootstrap-admin` once (via the
  Swagger UI or curl) to create the first admin account — this endpoint
  disables itself automatically once any user exists. See
  `docs/DEPLOYMENT.md` for the exact command.

## Quick start (local development, no Docker)

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate

# Requires the tesseract-ocr system package: `apt install tesseract-ocr` (Linux) / `brew install tesseract` (Mac)
cp .env.example .env
python -m scripts.seed          # creates demo admin/officer accounts + sample products
uvicorn app.main:app --reload --port 8000
```
Demo logins printed by the seed script:
`admin@legalmetrology.gov.in` / `officer@legalmetrology.gov.in`, password `ChangeMe@123`
— **change these immediately outside of local development.**

**Frontend**
```bash
cd frontend
npm install
npm run dev       # http://localhost:5173, proxies /api to localhost:8000
```

## Running tests

```bash
cd backend
pytest tests/ -v
```

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system design, data flow, scaling notes
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — production deployment guide
- [`docs/API.md`](docs/API.md) — REST API reference
- [`docs/LEGAL_METROLOGY_RULES_MAPPING.md`](docs/LEGAL_METROLOGY_RULES_MAPPING.md) — how each Rule 6 declaration maps to a detection rule, and its limitations

## Important limitations (read before relying on this for enforcement)

- **This is a decision-support tool, not a legal authority.** Every report
  carries a disclaimer and is designed around an officer review/finalize
  workflow — nothing here issues a penalty or legal notice automatically.
- **OCR is not perfect.** Poor lighting, glare, non-Latin scripts, or damaged
  labels can cause false "missing declaration" flags. Officers should
  visually verify anything the system flags as non-compliant before acting.
- **Font-size measurement in millimetres requires physical calibration**
  (a reference object in frame, or a known camera-to-label distance).
  Without it, measurements are marked `"estimated"` and should be treated as
  indicative only — see `docs/LEGAL_METROLOGY_RULES_MAPPING.md`.
- **The legal rule text is encoded as editable configuration**
  (`backend/app/rules/*.json`), not hardcoded, specifically so a Legal
  Metrology / legal officer can review and correct it against the current
  Gazette-notified Rules before production use. Treat the shipped values as a
  reasonable starting point, not verified legal text.

## License / attribution

Reference implementation built against publicly available summaries of the
Legal Metrology Act, 2009 and the Legal Metrology (Packaged Commodities)
Rules, 2011 (see https://consumeraffairs.gov.in/pages/legal-metrology-act).
Not affiliated with or endorsed by the Department of Consumer Affairs.pip install -r requirements.txt
