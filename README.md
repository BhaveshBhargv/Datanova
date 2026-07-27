# DataNova

An end-to-end data analytics platform combining data science, machine learning, AI, and
modern software engineering. Upload datasets or connect a SQL database, then profile,
clean, explore, model, explain, and **chat with your data** through an LLM-powered
analytics assistant — with dashboards and exportable reports.

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLAlchemy, Alembic |
| Database | PostgreSQL |
| Data science | Pandas, NumPy, scikit-learn, XGBoost, SHAP |
| Frontend | React, TypeScript, Tailwind CSS, Apache ECharts |
| AI / LLM | OpenRouter (OpenAI-compatible), configurable model |
| Auth | JWT (access + refresh) |
| Deployment | Render (backend), Vercel (frontend) |

## Roadmap (11 phases → milestones)

1. **Foundation & Auth** — project architecture, backend, frontend, DB, JWT login ✅
2. **Data Ingestion** — CSV/Excel upload + SQL DB connections ✅
3. **Profiling & Cleaning** — missing/duplicates/outliers/types + transformation history ✅
4. **EDA & Visualization** — auto stats + ECharts + AI chart explanations ✅
5. **Conversational AI Assistant** — NL Q&A → SQL + business explanations ✅
6. **AutoML** — auto problem detection, multi-model training, comparison ✅
7. **Explainable AI** — SHAP feature importance + prediction explanations ✅
8. **NL→SQL Engine** — safe NL-to-SQL: validate, execute, optimize, explain ✅
   _← current_
9. **Insights & Recommendations** — trends, anomalies, actionable recommendations
10. **Reporting & Export** — PDF/Excel reports with visuals, stats, AI summaries
11. **Analytics Workspace** — manage datasets, dashboards, saved analyses, history

## Project structure

```
DataNova/
├── backend/     # FastAPI app, SQLAlchemy, Alembic, ML services
├── frontend/    # React + TS + Tailwind + ECharts (Vite)
├── docs/        # architecture & API contract
└── docker-compose.yml
```

## Running locally

**Prerequisites:** Python 3.12+, Node 18+. PostgreSQL 16 and/or Docker are optional —
for a quick local run you can use SQLite (see Option B).

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Frontend | http://localhost:5173 |

### 1. Configure environment

```bash
cp backend/.env.example backend/.env      # Windows: copy backend\.env.example backend\.env
cp frontend/.env.example frontend/.env
```

Then edit `backend/.env`:

| Variable | Notes |
|----------|-------|
| `SECRET_KEY` | Required. Generate one: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `DATABASE_URL` | Postgres by default; set to SQLite for Option B (below) |
| `OPENROUTER_API_KEY` | **Optional.** Without it, AI explanations use a rule-based fallback and the chat assistant is disabled. Get one at https://openrouter.ai/keys |
| `BACKEND_CORS_ORIGINS` | Must include the frontend origin (`http://localhost:5173` by default) |

> `backend/.env` and `frontend/.env` are gitignored — never commit real secrets.
> Keep real keys out of `.env.example` (it is committed).

### 2. Backend

**Option A — Docker (PostgreSQL + backend + migrations):**
```bash
docker-compose up --build
```
This starts Postgres, runs `alembic upgrade head`, and serves the API on :8000.

**Option B — Native, no Docker (SQLite):**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```
Set `DATABASE_URL=sqlite:///./dev.db` in `backend/.env`, then create the tables and run:
```bash
python -c "from app.core.database import Base, engine; import app.models; Base.metadata.create_all(engine)"
python -m uvicorn app.main:app --reload
```

> **Migrations vs. SQLite:** the Alembic migrations use PostgreSQL types (JSONB, UUID),
> so `alembic upgrade head` targets Postgres. On SQLite, create the schema with the
> `create_all` one-liner above instead (models use a portable schema at runtime).
> If you run your own local Postgres, use `alembic upgrade head` instead of `create_all`.

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```

## Tests
```bash
cd backend && pytest
```

See [`docs/architecture.md`](docs/architecture.md) and [`docs/api-contract.md`](docs/api-contract.md).
