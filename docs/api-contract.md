# API Contract — Phase 1

Base URL: `/api`  ·  Interactive docs: `/docs`

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
