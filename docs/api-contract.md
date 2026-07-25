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
