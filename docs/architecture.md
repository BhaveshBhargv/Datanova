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

## Profiling & cleaning (Phase 3)

- **Profiling** (`services/profile.py`) — dataset- and column-level quality stats,
  IQR outlier counts, and type suggestions for text columns that look
  numeric/datetime/boolean/categorical, plus a heuristic quality score.
- **Cleaning** (`services/transform.py` + `services/cleaning.py`) — a **replay-from-original**
  model: the ingested Parquet is immutable; each cleaning step is stored in the
  `transformations` table, and the current data (`cleaned_path`) is the original replayed
  through all steps. This gives history, **undo**, and **reset** deterministically. Steps are
  validated by dry-running them against the current data before being persisted.

Seven operations are supported: drop duplicates, drop missing rows, drop/rename columns,
impute missing (mean/median/mode/constant), cast type, and handle outliers (clip/remove).

## EDA & visualization (Phase 4)

- **`services/eda.py`** — numeric summaries, correlation matrix, and rule-based chart
  recommendations from column types.
- **`services/charts.py`** — computes ECharts-ready aggregates server-side for 7 chart
  types (histogram, bar, pie, box, scatter, correlation heatmap, line). Only small
  summaries cross the wire; the React `<Chart>` wrapper renders them with Apache ECharts.
- **`services/llm.py`** — thin OpenRouter (OpenAI-compatible) client over `httpx`. No key ⇒
  disabled.
- **`services/narrate.py`** — grounds an explanation: it recomputes stats server-side,
  builds the prompt from those facts (so client text can't inject), calls the LLM, and
  falls back to a deterministic rule-based narrative when the LLM is unavailable. Every
  explanation reports its `source` (`llm` or `fallback`).

The LLM provider/model are env-configured (`OPENROUTER_API_KEY`, `LLM_MODEL`, …); the app
is fully functional without a key.

## Conversational assistant (Phase 5)

- **`services/sql_safety.py`** — shared read-only SQL guard (single statement,
  SELECT/WITH only, keyword denylist), used by both DB import and the assistant.
- **`services/assistant.py`** — grounded NL→SQL: loads the current data into a throwaway
  **in-memory SQLite** table `data`, asks the LLM for a read-only SELECT, validates it,
  runs it (row-capped) on the isolated copy, then asks the LLM to explain the result.
  No filesystem/network reach and no access to the application database. Degrades
  gracefully to a message when no API key is set.

Conversations and messages persist in the `conversations`/`messages` tables. Result
tables that have one categorical + one numeric column are auto-charted on the frontend
using the Phase 4 ECharts layer.

## AutoML (Phase 6)

- **`services/automl.py`** — `detect_problem_type()` (classification vs regression from the
  target's dtype/cardinality), a scikit-learn `ColumnTransformer` preprocessor (impute + scale
  numeric, impute + one-hot categorical; datetime and very high-cardinality columns dropped),
  and `train()` which fits a roster (Logistic/Linear Regression, Decision Tree, Random Forest,
  XGBoost) on a holdout split, scores each, picks the best, and refits it on all data.
- The best pipeline is serialized with `joblib` through the `storage` abstraction (`model_path`
  on the experiment) for reuse in Phase 7 (SHAP) and future predictions.
- Training runs **synchronously in a threadpool** (`run_in_threadpool`) so it doesn't block the
  event loop; the request returns the finished leaderboard. Row-capped via `AUTOML_MAX_ROWS`.

Experiments persist in the `experiments` table (config, per-model metrics, best model, status).

## Explainable AI / SHAP (Phase 7)

- **`services/explain_ml.py`** — loads the saved best pipeline (joblib), runs the
  model-appropriate SHAP explainer (`TreeExplainer` for tree/boosting models,
  `LinearExplainer` for linear) on a sample of the current data, and **aggregates SHAP
  values from one-hot encoded columns back to the original features** using the fitted
  `ColumnTransformer`. Provides `global_importance()` and `explain_prediction()` (per-row
  contributions, predicted label + probabilities, base value).
- Reuses `narrate.explain_drivers()` for a plain-English, LLM-or-fallback summary of the
  key drivers.
- No schema change — explanations are computed on demand from the persisted model artifact.
  SHAP compute runs in a threadpool and samples up to `SHAP_SAMPLE` rows.

## Extending in later phases

New resources (models, reports, dashboards) follow the same vertical slice:
`models/` → Alembic migration → `schemas/` → `crud/` → optional `services/` → `api/routes/`.
This keeps each phase an additive, reviewable change.
