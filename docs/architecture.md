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

## Extending in later phases

New resources (datasets, models, reports, dashboards) follow the same vertical slice:
`models/` → Alembic migration → `schemas/` → `crud/` → `api/routes/`. This keeps each
phase an additive, reviewable change.
