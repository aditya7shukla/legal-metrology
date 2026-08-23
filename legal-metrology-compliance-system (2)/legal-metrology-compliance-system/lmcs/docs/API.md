# API Reference

Full interactive documentation (auto-generated from the FastAPI schema) is
always available at:

- Swagger UI: `/api/docs`
- ReDoc: `/api/redoc`
- Raw OpenAPI JSON: `/api/openapi.json`

This document summarizes the key endpoints for quick reference. All
endpoints below are prefixed with `/api/v1` and require an
`Authorization: Bearer <access_token>` header unless noted otherwise.

## Authentication

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/bootstrap-admin` | none | One-time: creates the first admin account. Self-disables once any user exists. |
| POST | `/auth/register` | admin | Create a new user (admin/officer/viewer). |
| POST | `/auth/login` | none | Returns `{ access_token, refresh_token, user }`. |
| POST | `/auth/refresh` | none (refresh token in body) | Rotates access + refresh tokens. |
| GET | `/auth/me` | any | Returns the current authenticated user. |

## Products (repository)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/products` | admin, officer | Create a repository entry. |
| GET | `/products?q=&category=&is_imported=&page=&page_size=` | any | Search/paginate the repository. |
| GET | `/products/{id}` | any | Get one product. |
| GET | `/products/{id}/history` | any | Product details + every scan/report for it. |

## Scans

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/scans` | admin, officer | Multipart upload: `image` (file) + `product_id` **or** `new_product` (JSON string) + `listing_type` + optional `panel_area_cm2`, `calibration_mm_per_px`, location fields. Runs the full OCR → rule-engine → report pipeline synchronously and returns the completed `ScanRecord` (including `report_id`). |
| GET | `/scans?product_id=&status=&page=&page_size=` | any | List/filter scans. |
| GET | `/scans/{id}` | any | Get one scan, including raw OCR text and font analysis. |

### Example: create a scan

```bash
curl -X POST http://localhost:8000/api/v1/scans \
  -H "Authorization: Bearer $TOKEN" \
  -F "image=@label_photo.jpg" \
  -F "product_id=<existing-product-uuid>" \
  -F "listing_type=physical_package" \
  -F "inspection_location_text=Retail Store, Sector 18, Noida"
```

To register a brand-new product inline instead of `product_id`:
```bash
-F 'new_product={"name":"Refined Oil 1L","brand":"SunGold","category":"food"}'
```

## Compliance reports

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/reports?overall_status=&is_finalized=&page=&page_size=` | any | List/filter reports. |
| GET | `/reports/{id}` | any | Full report with all violation details. |
| PATCH | `/reports/{id}/review` | admin, officer | Add `reviewer_notes`, set `override_status`, and/or `is_finalized`. |
| GET | `/reports/{id}/download/pdf` | any | Fixed evidentiary PDF. |
| GET | `/reports/{id}/download/docx` | any | Editable DOCX draft. |

## Dashboard

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/dashboard/summary?days=30` | any | Totals, compliance rate, top violation types, scans-by-day, scans-by-category. |

## Roles

| Role | Can do |
|---|---|
| `admin` | Everything, including creating users. |
| `officer` | Create products, run scans, review/finalize reports. Cannot manage users. |
| `viewer` | Read-only: browse repository, reports, dashboard. Cannot scan or review. |

## Error format

Errors follow FastAPI's default shape:
```json
{ "detail": "Human-readable message" }
```
or, for validation errors, a `detail` array with per-field messages.

## Pagination

List endpoints return:
```json
{ "total": 123, "page": 1, "page_size": 20, "items": [ ... ] }
```
