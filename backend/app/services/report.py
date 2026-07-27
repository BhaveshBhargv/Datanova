"""Assemble a comprehensive analytics report from all prior phases.

Gathers profiling, EDA, insights, the latest AutoML experiment + SHAP importances,
and AI narratives into a single serializable dict that the PDF/Excel renderers consume.
"""
from __future__ import annotations

import json

import pandas as pd
from sqlalchemy.orm import Session

from app.crud import experiment as experiment_crud
from app.models.dataset import Dataset
from app.models.experiment import STATUS_COMPLETED
from app.services import cleaning, eda, explain_ml, insights as insights_service
from app.services import narrate, profile


def _latest_completed_experiment(db: Session, dataset_id):
    for exp in experiment_crud.list_for_dataset(db, dataset_id):
        if exp.status == STATUS_COMPLETED and exp.model_path:
            return exp
    return None


def assemble(db: Session, dataset: Dataset) -> dict:
    df = cleaning.load_current(dataset)

    prof = profile.profile_dataframe(df)
    eda_summary = eda.summary(df)
    experiment = _latest_completed_experiment(db, dataset.id)
    insight_items = insights_service.generate_insights(df, experiment)

    importance = None
    experiment_info = None
    if experiment:
        experiment_info = {
            "target": experiment.target_column,
            "problem_type": experiment.problem_type,
            "best_model_name": experiment.best_model_name,
            "results": experiment.results or [],
        }
        try:
            importance = explain_ml.global_importance(experiment, df)["importance"]
        except Exception:  # noqa: BLE001 - SHAP is best-effort in a report
            importance = None

    overview_text, overview_source = narrate.explain(df, "overview", None)
    insights_text, insights_source = narrate.explain_insights(insight_items)

    head = df.head(20)
    preview = {
        "columns": [str(c) for c in head.columns],
        "rows": json.loads(head.to_json(orient="records", date_format="iso")),
    }

    return {
        "dataset": {
            "name": dataset.name,
            "n_rows": dataset.n_rows,
            "n_columns": dataset.n_columns,
            "source_type": dataset.source_type,
            "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
        },
        "profile": prof,
        "eda": eda_summary,
        "experiment": experiment_info,
        "importance": importance,
        "insights": insight_items,
        "insights_counts": insights_service.counts(insight_items),
        "summary": {
            "overview": overview_text,
            "overview_source": overview_source,
            "insights": insights_text,
            "insights_source": insights_source,
        },
        "preview": preview,
    }
