import { useEffect, useState } from "react";
import { downloadReport, getReport, type ReportData } from "../lib/report";

function Badge({ source }: { source: "llm" | "fallback" }) {
  return (
    <span
      className={`ml-1 rounded px-1.5 py-0.5 text-xs font-medium ${
        source === "llm"
          ? "bg-indigo-50 text-indigo-700"
          : "bg-slate-100 text-slate-500"
      }`}
    >
      {source === "llm" ? "AI" : "rule-based"}
    </span>
  );
}

export default function ReportPanel({
  datasetId,
  datasetName,
  version,
}: {
  datasetId: string;
  datasetName: string;
  version: number;
}) {
  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<"pdf" | "excel" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getReport(datasetId)
      .then(setReport)
      .catch(() => setError("Could not assemble the report."))
      .finally(() => setLoading(false));
  }, [datasetId, version]);

  async function onDownload(format: "pdf" | "excel") {
    setBusy(format);
    setError(null);
    try {
      await downloadReport(datasetId, format, datasetName);
    } catch {
      setError("Download failed. Please try again.");
    } finally {
      setBusy(null);
    }
  }

  if (loading) return <p className="text-sm text-slate-500">Assembling report…</p>;
  if (!report) return <p className="text-sm text-red-600">{error ?? "No report."}</p>;

  const included = [
    { label: "Data quality", detail: `Quality score ${report.profile.quality_score}` },
    {
      label: "Exploratory analysis",
      detail: `${report.eda.correlations.columns.length} numeric columns, correlation heatmap`,
    },
    {
      label: "Insights & recommendations",
      detail: `${report.insights_counts.critical} critical · ${report.insights_counts.warning} warning · ${report.insights_counts.info} info`,
    },
    {
      label: "Model performance",
      detail: report.experiment
        ? `${report.experiment.best_model_name} on '${report.experiment.target}'`
        : "No trained model yet",
    },
    { label: "Data preview", detail: "First rows of the dataset" },
  ];

  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="eyebrow">Export</p>
          <h2 className="mt-1 font-display text-xl font-bold text-ink">Analytics report</h2>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => onDownload("pdf")}
            disabled={busy !== null}
            className="btn-nova disabled:opacity-60"
          >
            {busy === "pdf" ? "Preparing…" : "Download PDF"}
          </button>
          <button
            onClick={() => onDownload("excel")}
            disabled={busy !== null}
            className="btn-ghost disabled:opacity-60"
          >
            {busy === "excel" ? "Preparing…" : "Download Excel"}
          </button>
        </div>
      </div>

      {error && <p className="mt-3 text-sm text-nova-700">{error}</p>}

      {/* Executive summary preview */}
      <div className="mt-5 rounded-2xl border border-nova-100 bg-nova-50/50 p-5">
        <p className="eyebrow text-nova-500">Executive summary</p>
        <p className="mt-2 text-sm leading-relaxed text-ink">
          {report.summary.overview}
          <Badge source={report.summary.overview_source} />
        </p>
        <p className="mt-2 text-sm leading-relaxed text-ink">
          {report.summary.insights}
          <Badge source={report.summary.insights_source} />
        </p>
      </div>

      {/* What's included */}
      <div className="card mt-5 p-5">
        <p className="eyebrow">Contents</p>
        <ul className="mt-3 divide-y divide-line">
          {included.map((s) => (
            <li key={s.label} className="flex items-start gap-3 py-2.5 text-sm">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-nova-500" />
              <span>
                <span className="font-medium text-ink">{s.label}</span>
                <span className="text-slate-500"> — {s.detail}</span>
              </span>
            </li>
          ))}
        </ul>
        <p className="mt-4 font-mono text-[11px] text-slate-400">
          PDF · formatted report with charts   ·   XLSX · multi-sheet workbook
        </p>
      </div>
    </div>
  );
}
