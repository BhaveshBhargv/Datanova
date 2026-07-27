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

# Phase 5

Conversational assistant. The dataset's current data is loaded into an isolated
in-memory SQLite table named `data`; the LLM writes a **read-only SELECT**, which is
validated and executed there, then explained. All 🔒, ownership-scoped via the dataset.

### `GET /api/datasets/{id}/conversations`  🔒
List the dataset's conversation threads.

### `POST /api/datasets/{id}/conversations`  🔒
Body `{ "title": "Chat" }` → new conversation.

### `GET /api/conversations/{cid}`  🔒
Conversation with its ordered messages.

### `POST /api/conversations/{cid}/messages`  🔒
Ask a question. Body `{ "content": "What is average income by region?" }`.
Persists the user message, runs the assistant, and returns the assistant reply:
```json
{
  "role": "assistant",
  "content": "The West region has the highest average income…",
  "sql": "SELECT \"region\", AVG(\"income\") AS avg_income FROM data GROUP BY \"region\" ORDER BY avg_income DESC",
  "result_columns": ["region", "avg_income"],
  "result_rows": [{"region":"west","avg_income":55937.7}, "..."],
  "error": null
}
```
If the generated SQL is not a single read-only statement it is **rejected** (not
executed) and `error` is set. Without an API key the reply is a graceful message and
nothing is executed.

### `DELETE /api/conversations/{cid}`  🔒
`204 No Content`.

# Phase 6

AutoML. Training runs synchronously in a worker thread and returns the completed
experiment. All 🔒, ownership-scoped.

### `POST /api/datasets/{id}/experiments`  🔒
Body `{ "target": "churned", "features"?: [...], "test_size"?: 0.2 }`. Detects the
problem type, trains the model roster on a holdout split, persists the best pipeline,
and returns the completed experiment:
```json
{
  "problem_type": "classification",
  "status": "completed",
  "target_column": "churned",
  "feature_columns": ["tenure_months","monthly_charges","age","plan"],
  "best_model_name": "Random Forest",
  "results": [
    {"model":"Logistic Regression","metrics":{"accuracy":0.75,"precision":0.64,"recall":0.59,"f1":0.60,"roc_auc":0.73}},
    {"model":"Random Forest","metrics":{"accuracy":0.77,"f1":0.62, "...":"..."}}
  ]
}
```
Roster: Logistic/Linear Regression, Decision Tree, Random Forest, XGBoost. Metrics —
classification: accuracy, precision, recall, F1 (macro), ROC-AUC (binary); regression:
R², RMSE, MAE. `400` for an invalid target/features; training failures return the
experiment with `status:"failed"` and `error`.

### `GET /api/datasets/{id}/experiments`  🔒
List the dataset's experiments (newest first).

### `GET /api/experiments/{eid}`  🔒
Experiment detail (leaderboard + best model).

### `DELETE /api/experiments/{eid}`  🔒
Deletes the experiment and its saved model artifact. `204 No Content`.

# Phase 7

SHAP explanations for a **completed** experiment's best model. All 🔒, ownership-scoped.
`409` if the experiment isn't completed / has no saved model.

### `GET /api/experiments/{eid}/importance`  🔒
Global feature importance (mean |SHAP|), aggregated back to original features:
```json
{
  "problem_type": "classification", "target": "churned", "sample_size": 220,
  "importance": [
    {"feature": "monthly_charges", "importance": 0.1312},
    {"feature": "tenure_months", "importance": 0.1254},
    {"feature": "age", "importance": 0.0486}
  ]
}
```

### `POST /api/experiments/{eid}/predictions/explain`  🔒
Explain the model's prediction for a dataset row. Body `{ "index": 0 }`:
```json
{
  "index": 0, "prediction": 0, "predicted_label": 0,
  "proba": {"0": 0.97, "1": 0.03}, "base_value": 0.31,
  "contributions": [
    {"feature": "monthly_charges", "value": 28, "contribution": 0.196},
    {"feature": "tenure_months", "value": 40, "contribution": -0.041}
  ]
}
```
Contributions are per original feature (one-hot columns summed), ordered by magnitude;
positive pushes the prediction up, negative pushes it down. `400` if the index is out of range.

### `POST /api/experiments/{eid}/narrative`  🔒
Plain-English summary of the model's key drivers from the SHAP importances →
`{ "text": "…", "source": "llm" | "fallback" }` (rule-based fallback when no API key).

# Phase 8

NL→SQL over a **live connected database** (Phase 2 connections). All 🔒, ownership-scoped.
Read-only, row-capped, with a statement timeout. Queries are saved to a per-connection history.

### `GET /api/connections/{cid}/schema`  🔒
Introspected schema: `{ "tables": [{ "table": "orders", "columns": [{"name":"amount","type":"REAL"}] }] }`.

### `POST /api/connections/{cid}/query`  🔒
Body `{ "question": "total order amount by country?" }`. Generates dialect-aware SQL,
validates it read-only, runs EXPLAIN, executes (capped), and explains:
```json
{
  "sql": "WITH order_country AS (...) SELECT country, SUM(amount) AS total_amount ... ORDER BY total_amount DESC",
  "columns": ["country","total_amount"],
  "rows": [{"country":"UK","total_amount":15456.25}, "..."],
  "row_count": 5,
  "plan": ["SCAN o", "SEARCH c USING INTEGER PRIMARY KEY", "..."],
  "optimization_notes": ["No WHERE clause — this may scan the entire table.", "..."],
  "explanation": "The UK leads with the highest total order amount at $15,456.25…",
  "source": "llm", "error": null
}
```
Unsafe generated SQL is rejected (not executed) with `error` set; without an API key the
response is a graceful message and nothing runs. Every call is persisted to history.

### `GET /api/connections/{cid}/queries`  🔒
Recent query history (question, sql, explanation, source, row_count, error, created_at).

### `DELETE /api/connections/{cid}/queries/{qid}`  🔒
Remove a history entry. `204 No Content`.

# Phase 9

Auto-generated insights & recommendations. Grounded (rule-based) findings, incorporating
the latest completed AutoML experiment + SHAP when present. All 🔒, ownership-scoped.

### `GET /api/datasets/{id}/insights`  🔒
```json
{
  "total": 5,
  "counts": { "critical": 1, "warning": 2, "info": 2 },
  "insights": [
    { "category": "data_quality", "severity": "critical",
      "title": "'mostly_missing' is 96.77% missing",
      "detail": "58 of 62 values are missing.",
      "recommendation": "Impute (mean/median/mode) or drop this column." },
    { "category": "model", "severity": "info",
      "title": "Top predictors of 'churned': monthly_charges, tenure_months, age",
      "detail": "These features most influence the model's predictions (SHAP).",
      "recommendation": "Prioritize 'monthly_charges' for interventions and monitoring." }
  ]
}
```
Categories: `data_quality`, `statistical`, `anomaly`, `trend`, `model`. Severity-ranked
(critical → warning → info). Every claim is computed, not generated.

### `POST /api/datasets/{id}/insights/narrative`  🔒
LLM business summary of the insights → `{ "text": "…", "source": "llm" | "fallback" }`
(deterministic fallback when no API key or the model is unavailable).
