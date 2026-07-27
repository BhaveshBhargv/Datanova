"""Render an assembled report dict to a PDF (ReportLab + matplotlib charts)."""
from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_METRIC_ORDER = {
    "classification": ["accuracy", "precision", "recall", "f1", "roc_auc"],
    "regression": ["r2", "rmse", "mae"],
}
_SEVERITY_COLOR = {"critical": "#dc2626", "warning": "#d97706", "info": "#4f46e5"}


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("H2b", parent=styles["Heading2"], textColor=colors.HexColor("#1e293b")))
    styles.add(ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#475569")))
    return styles


def _fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)


def _table(data, col_widths=None, header=True) -> Table:
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(style))
    return t


def _fig_to_image(fig, width_cm=15) -> Image:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    ratio = fig.get_figheight() / fig.get_figwidth()
    width = width_cm * cm
    return Image(buf, width=width, height=width * ratio)


def _heatmap_image(correlations) -> Image | None:
    cols = correlations.get("columns", [])
    matrix = correlations.get("matrix", [])
    if len(cols) < 2:
        return None
    data = np.array([[(v if v is not None else 0.0) for v in row] for row in matrix])
    size = min(6.0, 1.5 + 0.5 * len(cols))
    fig, ax = plt.subplots(figsize=(size, size))
    im = ax.imshow(data, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels(cols, rotation=45, ha="right", fontsize=7)
    ax.set_yticks(range(len(cols)))
    ax.set_yticklabels(cols, fontsize=7)
    for i in range(len(cols)):
        for j in range(len(cols)):
            ax.text(j, i, f"{data[i, j]:.2f}", ha="center", va="center", fontsize=6)
    fig.colorbar(im, shrink=0.7)
    return _fig_to_image(fig, width_cm=12)


def _importance_image(importance) -> Image | None:
    if not importance:
        return None
    top = importance[:12][::-1]
    names = [i["feature"] for i in top]
    vals = [i["importance"] for i in top]
    fig, ax = plt.subplots(figsize=(6, max(2.0, 0.4 * len(top))))
    ax.barh(names, vals, color="#4f46e5")
    ax.set_xlabel("mean |SHAP|", fontsize=8)
    ax.tick_params(labelsize=7)
    return _fig_to_image(fig, width_cm=14)


def build_pdf(report: dict) -> bytes:
    styles = _styles()
    out = io.BytesIO()
    doc = SimpleDocTemplate(out, pagesize=A4, title=f"{report['dataset']['name']} report")
    el = []

    ds = report["dataset"]
    prof = report["profile"]

    # --- Title ---
    el.append(Paragraph(f"Analytics Report — {ds['name']}", styles["Title"]))
    el.append(Paragraph(f"Generated {ds.get('created_at', '')[:10]}", styles["Small"]))
    el.append(Spacer(1, 8))
    el.append(
        _table(
            [
                ["Rows", "Columns", "Quality score", "Missing cells", "Duplicate rows"],
                [
                    _fmt(ds["n_rows"]),
                    _fmt(ds["n_columns"]),
                    _fmt(prof["quality_score"]),
                    f"{prof['missing_cells']} ({prof['missing_pct']}%)",
                    _fmt(prof["duplicate_rows"]),
                ],
            ]
        )
    )
    el.append(Spacer(1, 12))

    # --- Executive summary ---
    el.append(Paragraph("Executive summary", styles["H2b"]))
    el.append(Paragraph(report["summary"]["overview"], styles["Normal"]))
    el.append(Spacer(1, 4))
    el.append(Paragraph(report["summary"]["insights"], styles["Normal"]))
    el.append(Spacer(1, 12))

    # --- Data quality ---
    el.append(Paragraph("Data quality", styles["H2b"]))
    quality_rows = [["Column", "Type", "Missing %", "Unique", "Outliers"]]
    for c in prof["columns"][:20]:
        quality_rows.append(
            [c["name"], c["dtype"], _fmt(c["missing_pct"]), _fmt(c["unique"]), _fmt(c.get("outliers"))]
        )
    el.append(_table(quality_rows))
    el.append(Spacer(1, 12))

    # --- EDA ---
    el.append(Paragraph("Exploratory analysis", styles["H2b"]))
    heatmap = _heatmap_image(report["eda"]["correlations"])
    if heatmap:
        el.append(Paragraph("Correlation heatmap", styles["Small"]))
        el.append(heatmap)
    else:
        el.append(Paragraph("Not enough numeric columns for correlations.", styles["Small"]))
    el.append(Spacer(1, 12))

    # --- Insights ---
    el.append(Paragraph("Insights & recommendations", styles["H2b"]))
    if not report["insights"]:
        el.append(Paragraph("No notable issues found.", styles["Small"]))
    for ins in report["insights"][:20]:
        color = _SEVERITY_COLOR.get(ins["severity"], "#334155")
        el.append(
            Paragraph(
                f'<font color="{color}"><b>[{ins["severity"].upper()}]</b></font> '
                f'<b>{ins["title"]}</b> — {ins["detail"]}',
                styles["Small"],
            )
        )
        if ins.get("recommendation"):
            el.append(Paragraph(f'→ {ins["recommendation"]}', styles["Small"]))
        el.append(Spacer(1, 3))
    el.append(Spacer(1, 12))

    # --- Model performance ---
    exp = report.get("experiment")
    if exp:
        el.append(Paragraph("Model performance", styles["H2b"]))
        el.append(
            Paragraph(
                f"Target: <b>{exp['target']}</b> ({exp['problem_type']}) · "
                f"Best model: <b>{exp['best_model_name']}</b>",
                styles["Small"],
            )
        )
        metric_keys = [
            k
            for k in _METRIC_ORDER.get(exp["problem_type"], [])
            if any(k in r["metrics"] for r in exp["results"])
        ]
        rows = [["Model", *metric_keys]]
        for r in exp["results"]:
            rows.append([r["model"], *[_fmt(r["metrics"].get(k)) for k in metric_keys]])
        el.append(_table(rows))
        el.append(Spacer(1, 6))
        imp_img = _importance_image(report.get("importance"))
        if imp_img:
            el.append(Paragraph("Feature importance (SHAP)", styles["Small"]))
            el.append(imp_img)
        el.append(Spacer(1, 12))

    # --- Data preview ---
    el.append(Paragraph("Data preview", styles["H2b"]))
    preview = report["preview"]
    cols = preview["columns"][:8]
    rows = [cols]
    for row in preview["rows"][:10]:
        rows.append([_fmt(row.get(c)) for c in cols])
    el.append(_table(rows))

    doc.build(el)
    return out.getvalue()
