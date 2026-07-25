# AI Data Analytics Platform

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
| Auth | JWT (access + refresh) |
| Deployment | Render (backend), Vercel (frontend) |

## Roadmap (11 phases → milestones)

1. **Foundation & Auth** — project architecture, backend, frontend, DB, JWT login ← _current_
2. **Data Ingestion** — CSV/Excel upload + SQL DB connections
3. **Profiling & Cleaning** — missing/duplicates/outliers/types + transformation history
4. **EDA & Visualization** — auto stats + ECharts + AI chart explanations
5. **Conversational AI Assistant** — NL Q&A → SQL/Python + business explanations
6. **AutoML** — auto problem detection, multi-model training, comparison
7. **Explainable AI** — SHAP feature importance + prediction explanations
8. **NL→SQL Engine** — safe NL-to-SQL: validate, execute, optimize, explain
9. **Insights & Recommendations** — trends, anomalies, actionable recommendations
10. **Reporting & Export** — PDF/Excel reports with visuals, stats, AI summaries
11. **Analytics Workspace** — manage datasets, dashboards, saved analyses, history

## Project structure

```
ai-analytics-platform/
├── backend/     # FastAPI app, SQLAlchemy, Alembic, auth
├── frontend/    # React + TS + Tailwind + ECharts (Vite)
├── docs/        # architecture & API contract
└── docker-compose.yml
```

## Quick start (local)

### 1. Database + backend via Docker
```bash
cp backend/.env.example backend/.env   # then edit secrets
docker-compose up --build
```
Backend: http://localhost:8000 · Docs: http://localhost:8000/docs

### 2. Backend without Docker
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### 3. Frontend
```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```
Frontend: http://localhost:5173

## Tests
```bash
cd backend && pytest
```

See [`docs/architecture.md`](docs/architecture.md) and [`docs/api-contract.md`](docs/api-contract.md).
