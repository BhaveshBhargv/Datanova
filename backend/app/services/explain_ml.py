"""SHAP-based explanations for a completed experiment's best model.

Loads the saved joblib pipeline, runs the model-appropriate SHAP explainer on the
current data, and aggregates SHAP values from one-hot encoded columns back to the
original feature names.
"""
from __future__ import annotations

import io
from typing import Any

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import (
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from xgboost import XGBClassifier, XGBRegressor

from app.core.config import settings
from app.core.storage import storage
from app.models.experiment import PROBLEM_CLASSIFICATION, Experiment

_TREE_MODELS = (
    RandomForestClassifier,
    RandomForestRegressor,
    DecisionTreeClassifier,
    DecisionTreeRegressor,
    XGBClassifier,
    XGBRegressor,
)


class ExplainError(Exception):
    """Raised when a model cannot be explained (-> HTTP 4xx)."""


def _load_pipeline(experiment: Experiment):
    if not experiment.model_path:
        raise ExplainError("This experiment has no saved model to explain.")
    return joblib.load(io.BytesIO(storage.read(experiment.model_path)))


def _feature_map(preprocessor) -> list[str]:
    """Original feature name for each column produced by the preprocessor, in order."""
    transformers = {name: cols for name, _, cols in preprocessor.transformers_}
    numeric = list(transformers.get("num", []))
    categorical = list(transformers.get("cat", []))

    mapping = list(numeric)  # numeric columns map 1:1
    if categorical:
        ohe = preprocessor.named_transformers_["cat"].named_steps["encode"]
        for col, categories in zip(categorical, ohe.categories_):
            mapping += [col] * len(categories)
    return mapping


def _explainer(model, background: np.ndarray):
    if isinstance(model, _TREE_MODELS):
        return shap.TreeExplainer(model)
    return shap.LinearExplainer(model, background)


def _shap_array(explainer, X: np.ndarray) -> np.ndarray:
    """Compute SHAP values, disabling the additivity check where supported (trees)."""
    try:
        return np.array(explainer.shap_values(X, check_additivity=False))
    except TypeError:
        return np.array(explainer.shap_values(X))


def _json_safe(value: Any):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (int, float, str, bool)):
        return value
    return str(value)


def _sample(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    X = df[features]
    if len(X) > settings.SHAP_SAMPLE:
        return X.sample(settings.SHAP_SAMPLE, random_state=0)
    return X


def _target_classes(df: pd.DataFrame, target: str) -> list:
    # LabelEncoder assigns codes in sorted order, so this reconstructs the mapping.
    return sorted(df[target].dropna().unique().tolist())


def global_importance(experiment: Experiment, df: pd.DataFrame) -> dict:
    pipeline = _load_pipeline(experiment)
    prep = pipeline.named_steps["prep"]
    model = pipeline.named_steps["model"]
    features = experiment.feature_columns

    sample = _sample(df, features)
    transformed = prep.transform(sample)
    feature_map = _feature_map(prep)

    explainer = _explainer(model, transformed)
    values = _shap_array(explainer, transformed)

    if values.ndim == 3:  # (n, features, classes)
        per_column = np.abs(values).mean(axis=(0, 2))
    else:  # (n, features)
        per_column = np.abs(values).mean(axis=0)

    aggregated: dict[str, float] = {}
    for name, imp in zip(feature_map, per_column):
        aggregated[name] = aggregated.get(name, 0.0) + float(imp)

    ranked = sorted(aggregated.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "problem_type": experiment.problem_type,
        "target": experiment.target_column,
        "sample_size": int(len(sample)),
        "importance": [
            {"feature": f, "importance": round(v, 6)} for f, v in ranked
        ],
    }


def explain_prediction(experiment: Experiment, df: pd.DataFrame, index: int) -> dict:
    if index < 0 or index >= len(df):
        raise ExplainError(f"Row index {index} is out of range (0–{len(df) - 1}).")

    pipeline = _load_pipeline(experiment)
    prep = pipeline.named_steps["prep"]
    model = pipeline.named_steps["model"]
    features = experiment.feature_columns

    row = df[features].iloc[[index]]
    transformed_row = prep.transform(row)
    background = prep.transform(_sample(df, features))
    feature_map = _feature_map(prep)

    explainer = _explainer(model, background)
    values = _shap_array(explainer, transformed_row)
    expected = np.array(explainer.expected_value)

    is_classification = experiment.problem_type == PROBLEM_CLASSIFICATION
    raw_pred = pipeline.predict(row)[0]

    predicted_label: Any = None
    proba = None
    if is_classification:
        classes = _target_classes(df, experiment.target_column)
        cls_index = int(raw_pred)
        predicted_label = _json_safe(classes[cls_index]) if cls_index < len(classes) else cls_index
        if hasattr(pipeline, "predict_proba"):
            probs = pipeline.predict_proba(row)[0]
            proba = {
                str(_json_safe(classes[i])): round(float(p), 4)
                for i, p in enumerate(probs)
            }
        if values.ndim == 3:  # (1, features, classes)
            contrib_values = values[0, :, cls_index]
            base_value = float(expected[cls_index]) if expected.ndim else float(expected)
        else:  # (1, features)
            contrib_values = values[0]
            base_value = float(expected) if expected.ndim == 0 else float(expected[0])
        prediction: Any = predicted_label
    else:
        contrib_values = values[0]
        base_value = float(expected) if expected.ndim == 0 else float(expected[0])
        prediction = round(float(raw_pred), 6)

    aggregated: dict[str, float] = {}
    for name, sv in zip(feature_map, contrib_values):
        aggregated[name] = aggregated.get(name, 0.0) + float(sv)

    contributions = [
        {
            "feature": f,
            "value": _json_safe(row.iloc[0][f]),
            "contribution": round(v, 6),
        }
        for f, v in sorted(aggregated.items(), key=lambda kv: abs(kv[1]), reverse=True)
    ]

    return {
        "index": index,
        "prediction": prediction,
        "predicted_label": predicted_label,
        "proba": proba,
        "base_value": round(base_value, 6),
        "contributions": contributions,
    }
