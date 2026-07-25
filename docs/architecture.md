# Architecture

## Overview

A monorepo with a FastAPI backend and a React (Vite) frontend, backed by PostgreSQL.
Phase 1 establishes the foundation: project structure, database, JWT authentication,
and a deploy skeleton.

```
┌────────────┐        HTTPS / JWT        ┌──────────────┐        SQL        ┌────────────┐
│  Frontend  │  ───────────────────────▶ │   Backend    │  ───────────────▶ │ PostgreSQL │
│ React + TS │  ◀─────────────────────── │   FastAPI    │  ◀─────────────── │            │
│  (Vercel)  │        JSON               │   (Render)   │                   │            │
└────────────┘                           └──────────────┘                   └────────────┘
```

## Backend layout (`backend/app`)

| Module | Responsibility |
|--------|----------------|
| `core/config.py` | Env-driven settings (Pydantic Settings) |
| `core/database.py` | SQLAlchemy engine, session, declarative `Base` |
| `core/security.py` | Password hashing (bcrypt) + JWT encode/decode |
| `core/types.py` | Portable `GUID` column type (UUID on PG, CHAR on SQLite) |
| `models/` | SQLAlchemy ORM models |
| `schemas/` | Pydantic request/response models |
| `crud/` | Database access helpers |
| `api/deps.py` | Shared dependencies (`get_current_user`) |
| `api/routes/` | Route handlers grouped by resource |
| `main.py` | App factory, CORS, router mounting, `/health` |

Database migrations live in `backend/alembic/` and are applied with `alembic upgrade head`.

## Authentication

- **Registration** stores a bcrypt hash; the plaintext password is never persisted.
- **Login** uses the OAuth2 password flow and returns a short-lived **access token**
  (30 min) plus a longer-lived **refresh token** (7 days), both HS256 JWTs.
- **Protected routes** depend on `get_current_user`, which validates the access token's
  signature, type, and expiry, then loads the active user.
- **Refresh** exchanges a valid refresh token for a new access token. Access tokens are
  explicitly rejected at the refresh endpoint (token `type` claim is checked).

## Frontend

- `lib/api.ts` — axios instance; attaches the bearer token and transparently refreshes
  it once on a 401.
- `context/AuthContext.tsx` — session state, login/register/logout, session restore.
- `components/ProtectedRoute.tsx` — gate for authenticated routes.
- `pages/` — Login, Register, Dashboard.

## Data ingestion (Phase 2)

Two ingestion paths land as **datasets**:

- **File upload** (`services/ingest.py`) — validates `.csv`/`.xlsx` (type, size, parseability),
  infers a column schema, stores the original file, and writes a **Parquet** copy for fast,
  dtype-stable reads in later phases.
- **Database import** (`services/db_import.py`) — builds a SQLAlchemy engine for
  PostgreSQL/MySQL/SQLite, tests connectivity, lists tables, and imports a table (reflected
  + row-capped `SELECT`) or a validated read-only query into a Parquet-backed dataset.

Supporting infrastructure:

| Module | Responsibility |
|--------|----------------|
| `core/storage.py` | Storage abstraction (`LocalStorage` now; S3 later) with path-traversal guards |
| `core/crypto.py` | Fernet field encryption for DB-connection passwords (never serialized back) |
| `core/types.py` | `GUID` + `JSONVariant` (JSONB on PostgreSQL, JSON on SQLite) |

Connection credentials are encrypted at rest; imports are read-only and row-capped. Reaching
arbitrary DB hosts is inherent to the feature (SSRF surface) — acceptable here; production would
add host allowlisting/egress proxying.

## Extending in later phases

New resources (models, reports, dashboards) follow the same vertical slice:
`models/` → Alembic migration → `schemas/` → `crud/` → optional `services/` → `api/routes/`.
This keeps each phase an additive, reviewable change.
