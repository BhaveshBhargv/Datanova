"""Rule-based, grounded insight generation.

Synthesizes profiling, EDA correlations, distribution/trend checks, and (when a
trained model exists) AutoML + SHAP results into categorized, severity-ranked
insights with actionable recommendations. Every claim is computed, not generated.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pandas.api.types as pdt

from app.models.experiment import STATUS_COMPLETED, Experiment
from app.services import eda, explain_ml, profile

_SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


def _numeric_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if pdt.is_numeric_dtype(df[c]) and not pdt.is_bool_dtype(df[c])]


def _datetime_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if pdt.is_datetime64_any_dtype(df[c])]


def _strong_pairs(corr: dict, threshold: float) -> list[tuple[str, str, float]]:
    cols, matrix = corr.get("columns", []), corr.get("matrix", [])
    pairs = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            v = matrix[i][j]
            if v is not None and abs(v) >= threshold:
                pairs.append((cols[i], cols[j], float(v)))
    return sorted(pairs, key=lambda t: abs(t[2]), reverse=True)


def _insight(category, severity, title, detail, recommendation=None) -> dict:
    return {
        "category": category,
        "severity": severity,
        "title": title,
        "detail": detail,
        "recommendation": recommendation,
    }


def generate_insights(
    df: pd.DataFrame, experiment: Experiment | None = None
) -> list[dict]:
    insights: list[dict] = []
    n_rows = int(len(df))
    if n_rows == 0:
        return insights

    prof = profile.profile_dataframe(df)
    columns = {c["name"]: c for c in prof["columns"]}

    # --- Data quality ---
    if prof["duplicate_rows"] > 0:
        pct = round(prof["duplicate_rows"] / n_rows * 100, 1)
        insights.append(
            _insight(
                "data_quality",
                "critical" if pct >= 10 else "warning",
                f"{prof['duplicate_rows']} duplicate rows ({pct}%)",
                "Duplicate rows can bias summaries and model training.",
                "Apply the 'drop duplicates' cleaning step.",
            )
        )

    for name, c in columns.items():
        mp = c["missing_pct"]
        sev = "critical" if mp >= 50 else "warning" if mp >= 20 else None
        if sev:
            insights.append(
                _insight(
                    "data_quality",
                    sev,
                    f"'{name}' is {mp}% missing",
                    f"{c['missing']} of {n_rows} values are missing.",
                    "Impute (mean/median/mode) or drop this column.",
                )
            )
        if c["unique"] <= 1:
            insights.append(
                _insight(
                    "data_quality",
                    "info",
                    f"'{name}' has a single value",
                    "Constant columns add no information.",
                    "Drop this column.",
                )
            )
        out = c.get("outliers")
        if out and c["count"] and out / c["count"] >= 0.05:
            pct = round(out / c["count"] * 100, 1)
            insights.append(
                _insight(
                    "anomaly",
                    "warning",
                    f"'{name}' has {out} outliers ({pct}%)",
                    "IQR-based outliers may distort statistics and models.",
                    "Review or clip outliers in the Cleaning tab.",
                )
            )
        if (
            c["dtype"] in ("string", "categorical")
            and c["count"]
            and c["unique"] == c["count"]
            and n_rows >= 10
        ):
            insights.append(
                _insight(
                    "data_quality",
                    "info",
                    f"'{name}' looks like an identifier",
                    "Every value is unique.",
                    "Exclude it from modeling and aggregations.",
                )
            )

    # --- Statistical ---
    for a, b, v in _strong_pairs(eda.correlations(df), 0.7):
        insights.append(
            _insight(
                "statistical",
                "info",
                f"Strong correlation: {a} & {b} ({v:+.2f})",
                "These variables move together; one may be redundant.",
                "Consider dropping one for modeling to reduce multicollinearity.",
            )
        )

    for name, c in columns.items():
        tv = c.get("top_values")
        if tv and c["count"] and c["unique"] > 1:
            share = tv[0]["count"] / c["count"]
            if share >= 0.8:
                insights.append(
                    _insight(
                        "statistical",
                        "warning",
                        f"'{name}' is dominated by '{tv[0]['value']}' ({round(share * 100)}%)",
                        "Highly imbalanced categories can bias analysis and models.",
                        "Group rare categories or resample for modeling.",
                    )
                )

    for name in _numeric_cols(df):
        s = df[name].dropna()
        if len(s) >= 8 and float(s.std()) > 0:
            skew = float(s.skew())
            if abs(skew) >= 1.5:
                insights.append(
                    _insight(
                        "statistical",
                        "info",
                        f"'{name}' is highly skewed (skew {skew:+.1f})",
                        "Skewed distributions can hurt linear models and summaries.",
                        "Consider a log or power transform.",
                    )
                )

    # --- Trend (datetime + numeric) ---
    dt_cols, num_cols = _datetime_cols(df), _numeric_cols(df)
    if dt_cols and num_cols:
        sub = df[[dt_cols[0], *num_cols]].dropna(subset=[dt_cols[0]]).sort_values(dt_cols[0])
        if len(sub) >= 8:
            order = np.arange(len(sub))
            for nc in num_cols[:3]:
                y = sub[nc].to_numpy(dtype="float64")
                if np.nanstd(y) > 0:
                    y = np.nan_to_num(y, nan=float(np.nanmean(y)))
                    r = float(np.corrcoef(order, y)[0, 1])
                    if abs(r) >= 0.5:
                        insights.append(
                            _insight(
                                "trend",
                                "info",
                                f"'{nc}' is {'increasing' if r > 0 else 'decreasing'} over {dt_cols[0]}",
                                f"Correlation with time order r={r:+.2f}.",
                                "Investigate what is driving this trend.",
                            )
                        )

    # --- Machine learning (if a completed experiment exists) ---
    if experiment and experiment.status == STATUS_COMPLETED and experiment.results:
        best = next(
            (r for r in experiment.results if r["model"] == experiment.best_model_name),
            None,
        )
        if best:
            primary = "f1" if experiment.problem_type == "classification" else "r2"
            val = best["metrics"].get(primary)
            insights.append(
                _insight(
                    "model",
                    "info",
                    f"Best model: {experiment.best_model_name} ({primary}={val})",
                    f"Trained to predict '{experiment.target_column}' ({experiment.problem_type}).",
                    "Open the Models tab's Explainability section to understand its drivers.",
                )
            )
        try:
            top = explain_ml.global_importance(experiment, df)["importance"][:3]
            if top:
                names = ", ".join(t["feature"] for t in top)
                insights.append(
                    _insight(
                        "model",
                        "info",
                        f"Top predictors of '{experiment.target_column}': {names}",
                        "These features most influence the model's predictions (SHAP).",
                        f"Prioritize '{top[0]['feature']}' for interventions and monitoring.",
                    )
                )
        except Exception:  # noqa: BLE001 - SHAP is best-effort here
            pass

    insights.sort(key=lambda i: _SEVERITY_ORDER.get(i["severity"], 3))
    return insights


def counts(insights: list[dict]) -> dict:
    result = {"critical": 0, "warning": 0, "info": 0}
    for i in insights:
        if i["severity"] in result:
            result[i["severity"]] += 1
    return result
