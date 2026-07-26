"""AutoML: detect problem type, build a preprocessing pipeline, train and compare models.

Trains a fixed roster of scikit-learn / XGBoost models on a holdout split and returns
per-model metrics plus the best refit pipeline (for persistence and Phase 7 SHAP).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pandas.api.types as pdt
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.impute import SimpleImputer
from xgboost import XGBClassifier, XGBRegressor

from app.core.config import settings
from app.models.experiment import PROBLEM_CLASSIFICATION, PROBLEM_REGRESSION

MAX_CATEGORICAL_CARDINALITY = 50


class AutoMLError(Exception):
    """Raised for invalid AutoML configurations (-> HTTP 400)."""


def detect_problem_type(y: pd.Series) -> str:
    y = y.dropna()
    if y.empty:
        raise AutoMLError("The target column has no non-missing values.")
    if pdt.is_bool_dtype(y):
        return PROBLEM_CLASSIFICATION
    if pdt.is_numeric_dtype(y):
        n_unique = y.nunique()
        integer_like = (y % 1 == 0).all()
        if n_unique <= 20 and integer_like:
            return PROBLEM_CLASSIFICATION
        return PROBLEM_REGRESSION
    return PROBLEM_CLASSIFICATION


def _split_feature_types(
    df: pd.DataFrame, features: list[str]
) -> tuple[list[str], list[str]]:
    numeric, categorical = [], []
    for col in features:
        s = df[col]
        if pdt.is_numeric_dtype(s) and not pdt.is_bool_dtype(s):
            numeric.append(col)
        elif pdt.is_datetime64_any_dtype(s):
            continue  # datetime not used as a feature in Phase 6
        elif s.nunique(dropna=True) <= MAX_CATEGORICAL_CARDINALITY:
            categorical.append(col)
        # very high-cardinality columns are dropped
    return numeric, categorical


def _build_preprocessor(numeric: list[str], categorical: list[str]) -> ColumnTransformer:
    numeric_pipe = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]
    )
    categorical_pipe = Pipeline(
        [
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        [
            ("num", numeric_pipe, numeric),
            ("cat", categorical_pipe, categorical),
        ]
    )


def _classification_models() -> dict:
    return {
        "Logistic Regression": LogisticRegression(max_iter=1000),
        "Decision Tree": DecisionTreeClassifier(random_state=0),
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=0, n_jobs=-1),
        "XGBoost": XGBClassifier(
            n_estimators=100, random_state=0, verbosity=0, eval_metric="logloss"
        ),
    }


def _regression_models() -> dict:
    return {
        "Linear Regression": LinearRegression(),
        "Decision Tree": DecisionTreeRegressor(random_state=0),
        "Random Forest": RandomForestRegressor(n_estimators=100, random_state=0, n_jobs=-1),
        "XGBoost": XGBRegressor(n_estimators=100, random_state=0, verbosity=0),
    }


def _classification_metrics(y_true, y_pred, y_proba) -> dict:
    metrics = {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 4),
    }
    if y_proba is not None and len(np.unique(y_true)) == 2:
        try:
            metrics["roc_auc"] = round(float(roc_auc_score(y_true, y_proba)), 4)
        except ValueError:
            metrics["roc_auc"] = None
    return metrics


def _regression_metrics(y_true, y_pred) -> dict:
    return {
        "r2": round(float(r2_score(y_true, y_pred)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
    }


def train(
    df: pd.DataFrame,
    target: str,
    features: list[str],
    problem_type: str,
    test_size: float,
) -> dict:
    """Train the roster and return {results, best_model_name, pipeline}."""
    data = df.dropna(subset=[target])
    if len(data) > settings.AUTOML_MAX_ROWS:
        data = data.sample(settings.AUTOML_MAX_ROWS, random_state=0)
    if len(data) < 10:
        raise AutoMLError("Not enough rows to train (need at least 10 after dropping missing targets).")

    numeric, categorical = _split_feature_types(data, features)
    used = numeric + categorical
    if not used:
        raise AutoMLError("No usable feature columns were found.")

    X = data[used]
    y = data[target]

    is_classification = problem_type == PROBLEM_CLASSIFICATION
    if is_classification:
        y = pd.Series(LabelEncoder().fit_transform(y), index=y.index)
        if y.nunique() < 2:
            raise AutoMLError("Classification needs at least two target classes.")

    stratify = y if (is_classification and y.value_counts().min() >= 2) else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=0, stratify=stratify
    )

    preprocessor = _build_preprocessor(numeric, categorical)
    models = _classification_models() if is_classification else _regression_models()

    results = []
    fitted: dict[str, Pipeline] = {}
    for name, estimator in models.items():
        pipe = Pipeline([("prep", preprocessor), ("model", estimator)])
        try:
            pipe.fit(X_train, y_train)
            y_pred = pipe.predict(X_test)
            if is_classification:
                proba = None
                if hasattr(pipe, "predict_proba") and len(np.unique(y_train)) == 2:
                    proba = pipe.predict_proba(X_test)[:, 1]
                metrics = _classification_metrics(y_test, y_pred, proba)
            else:
                metrics = _regression_metrics(y_test, y_pred)
            results.append({"model": name, "metrics": metrics})
            fitted[name] = pipe
        except Exception as exc:  # noqa: BLE001 - record a failed model, keep going
            results.append({"model": name, "metrics": {"error": str(exc)}})

    primary = "f1" if is_classification else "r2"
    scored = [r for r in results if isinstance(r["metrics"].get(primary), (int, float))]
    if not scored:
        raise AutoMLError("All models failed to train on this dataset.")
    best = max(scored, key=lambda r: r["metrics"][primary])
    best_name = best["model"]

    # Refit the best pipeline on all available data for the saved artifact.
    best_pipeline = Pipeline(
        [("prep", _build_preprocessor(numeric, categorical)), ("model", models[best_name])]
    )
    best_pipeline.fit(X, y)

    return {
        "results": results,
        "best_model_name": best_name,
        "used_features": used,
        "pipeline": best_pipeline,
    }
