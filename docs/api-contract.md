# API Contract

Base URL: `/api`  ·  Interactive docs: `/docs`

# Phase 1

## Health

### `GET /api/health`
Liveness probe.
```json
200 OK
{ "status": "ok", "environment": "development" }
```

## Auth

### `POST /api/auth/register`
Create a new account.
```json
// request
{ "email": "alice@example.com", "password": "supersecret123", "full_name": "Alice" }
```
```json
// 201 Created
{
  "id": "…uuid…",
  "email": "alice@example.com",
  "full_name": "Alice",
  "is_active": true,
  "created_at": "2026-07-25T10:00:00Z"
}
```
`409 Conflict` if the email is already registered.
`422` if the password is shorter than 8 characters or the email is invalid.

### `POST /api/auth/login`
OAuth2 password flow — send **form-encoded** fields, not JSON.
```
username=alice@example.com&password=supersecret123
```
```json
// 200 OK
{ "access_token": "…", "refresh_token": "…", "token_type": "bearer" }
```
`401 Unauthorized` on bad credentials.

### `POST /api/auth/refresh`
Exchange a refresh token for a fresh access token.
```json
// request
{ "refresh_token": "…" }
```
```json
// 200 OK
{ "access_token": "…", "token_type": "bearer" }
```
`401 Unauthorized` if the token is invalid, expired, or is an access token.

## Users

### `GET /api/users/me`  🔒
Requires `Authorization: Bearer <access_token>`.
```json
// 200 OK
{
  "id": "…uuid…",
  "email": "alice@example.com",
  "full_name": "Alice",
  "is_active": true,
  "created_at": "2026-07-25T10:00:00Z"
}
```
`401 Unauthorized` if the token is missing, invalid, or expired.

# Phase 2

All Phase 2 endpoints require `Authorization: Bearer <access_token>` and are
scoped to the current user (another user's resource returns `404`).

## Datasets

### `POST /api/datasets/upload`  🔒
Multipart upload of a `.csv` or `.xlsx` file (field name `file`).
Returns `201` with the created dataset (id, name, `source_type: "upload"`,
`n_rows`, `n_columns`, `columns: [{name, dtype, nullable}]`, `size_bytes`, …).
`400` for unsupported type, empty file, oversize (> 50 MB), or unparseable content.

### `GET /api/datasets`  🔒
List the current user's datasets (newest first).

### `GET /api/datasets/{id}`  🔒
Dataset metadata + inferred column schema. `404` if not found/owned.

### `GET /api/datasets/{id}/preview?rows=50`  🔒
`{ "columns": [...], "rows": [ {..}, .. ] }`. `rows` is clamped to 1–500;
missing values serialize as `null`.

### `PATCH /api/datasets/{id}`  🔒
Rename: `{ "name": "..." }` → updated dataset.

### `DELETE /api/datasets/{id}`  🔒
Deletes the record and its stored files. `204 No Content`.

## Connections

### `POST /api/connections`  🔒
Create + **test** a connection before persisting.
```json
{ "name": "warehouse", "dialect": "postgresql",
  "host": "db.example.com", "port": 5432,
  "database": "analytics", "username": "reader", "password": "…" }
```
`dialect` ∈ `postgresql | mysql | sqlite` (sqlite uses a file path in `database`
and needs no host). The password is Fernet-encrypted at rest and **never**
returned. `400` if the connection test fails; `422` if a server dialect lacks a host.

### `GET /api/connections`  🔒
List connections (no secrets).

### `POST /api/connections/{id}/test`  🔒
`{ "ok": true|false, "message": "..." }`.

### `GET /api/connections/{id}/tables`  🔒
`{ "tables": ["...", ...] }`.

### `POST /api/connections/{id}/import`  🔒
Import a table **or** a read-only query (exactly one) into a new dataset.
```json
{ "table": "customers" }            // or
{ "query": "SELECT ... ", "name": "optional" }
```
Row-capped (default 100k). Queries must be a single `SELECT`/`WITH`; write
keywords are rejected. Returns `201` with the created dataset
(`source_type: "database"`). `400` on import/validation failure.

### `DELETE /api/connections/{id}`  🔒
`204 No Content`.

# Phase 3

All Phase 3 endpoints require auth and are ownership-scoped. Profiling and preview
operate on the **current** data (original replayed through stored cleaning steps).

## Profiling

### `GET /api/datasets/{id}/profile`  🔒
Automated data-quality report:
```json
{
  "n_rows": 6, "n_columns": 3, "duplicate_rows": 1,
  "missing_cells": 1, "missing_pct": 5.56, "memory_bytes": 555,
  "quality_score": 86.2,
  "columns": [
    { "name": "score", "dtype": "float", "count": 5, "missing": 1,
      "missing_pct": 16.67, "unique": 4, "min": 10, "max": 1000,
      "mean": 208.8, "median": 11, "std": 441.9, "q1": 10.5, "q3": 12,
      "outliers": 1, "suggested_type": null },
    { "name": "city", "dtype": "string", "count": 6, "missing": 0,
      "unique": 2, "top_values": [{"value":"london","count":3}],
      "suggested_type": "category" }
  ]
}
```
Outliers use the IQR (1.5×) rule; `suggested_type` flags text columns that look
numeric/datetime/boolean/categorical. `quality_score` is a heuristic (100 minus
weighted penalties for missing %, duplicate %, and outlier %).

## Cleaning (reversible history)

The original ingested data is immutable; each step is stored and the current data
is the original **replayed** through all steps. Steps are validated (dry-run) before
being saved.

### `GET /api/datasets/{id}/transformations`  🔒
Ordered list of applied steps: `[{ id, order_index, operation, params, created_at }]`.

### `POST /api/datasets/{id}/transformations`  🔒
Apply a step; returns the updated dataset (new shape + schema).
```json
{ "operation": "impute_missing", "params": { "column": "score", "strategy": "median" } }
```
Operations: `drop_duplicates`, `drop_missing_rows`, `drop_columns`, `rename_columns`,
`impute_missing` (mean/median/mode/constant), `cast_type`
(integer/float/string/boolean/datetime/category), `handle_outliers` (clip/remove, IQR).
`400` if the step is invalid for the current data; `422` for an unknown operation.

### `POST /api/datasets/{id}/transformations/undo`  🔒
Remove the last step and replay. Returns the updated dataset.

### `POST /api/datasets/{id}/transformations/reset`  🔒
Clear all steps, reverting to the original. Returns the updated dataset.

# Phase 4

EDA, charting, and AI explanations — all 🔒, ownership-scoped, over the current data.

## EDA

### `GET /api/datasets/{id}/eda/summary`  🔒
```json
{
  "numeric": { "age": {"count":120,"mean":44.1,"std":13.2,"min":20,"max":64, "...":"..."} },
  "correlations": { "columns": ["age","income","spend"], "matrix": [[1.0,0.98,0.97], ...] },
  "recommended_charts": [
    { "type": "histogram", "column": "age", "reason": "Distribution of age" },
    { "type": "scatter", "x": "age", "y": "income", "reason": "Relationship between age and income" }
  ]
}
```

## Charts

### `POST /api/datasets/{id}/chart`  🔒
Body `ChartSpec { type, column?, x?, y?, bins?, top_n? }`. `type` ∈
`histogram | bar | pie | box | scatter | correlation_heatmap | line`.
Returns ECharts-ready data:
```json
{ "type":"histogram", "title":"Distribution of age", "x_label":"age", "y_label":"Count",
  "categories":["20.00–24.40", "..."], "series":[{"name":"age","data":[8,12,...]}], "extra":{} }
```
`400` for an unknown/non-applicable column; `422` for an unknown chart type.

## AI explanations

### `POST /api/datasets/{id}/explain`  🔒
Body `{ kind: "overview" | "chart", spec?: ChartSpec }`. The backend recomputes the
relevant stats server-side (grounded, injection-safe), prompts the LLM (OpenRouter),
and returns:
```json
{ "text": "…plain-English explanation…", "source": "llm" }
```
`source` is `"llm"` when `OPENROUTER_API_KEY` is configured and the call succeeds,
otherwise `"fallback"` (a deterministic rule-based narrative). The endpoint always
returns `200` with usable text.
