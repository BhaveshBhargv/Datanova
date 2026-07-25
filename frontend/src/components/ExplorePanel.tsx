import { useEffect, useMemo, useState } from "react";
import type { ColumnInfo } from "../lib/datasets";
import {
  explain,
  getEdaSummary,
  postChart,
  type ChartData,
  type ChartSpec,
  type ChartType,
  type EdaSummary,
  type ExplainResponse,
  type RecommendedChart,
} from "../lib/eda";
import { buildOption } from "../lib/echartsOption";
import Chart from "./Chart";

const CHART_LABELS: Record<ChartType, string> = {
  histogram: "Histogram",
  bar: "Bar",
  pie: "Pie",
  box: "Box plot",
  scatter: "Scatter",
  correlation_heatmap: "Correlation heatmap",
  line: "Line",
};

const NUMERIC = new Set(["integer", "float"]);

export default function ExplorePanel({
  datasetId,
  columns,
  version,
}: {
  datasetId: string;
  columns: ColumnInfo[];
  version: number;
}) {
  const numericCols = useMemo(
    () => columns.filter((c) => NUMERIC.has(c.dtype)).map((c) => c.name),
    [columns],
  );
  const allCols = useMemo(() => columns.map((c) => c.name), [columns]);

  const [summary, setSummary] = useState<EdaSummary | null>(null);
  const [type, setType] = useState<ChartType>("histogram");
  const [column, setColumn] = useState(numericCols[0] ?? allCols[0] ?? "");
  const [x, setX] = useState(numericCols[0] ?? "");
  const [y, setY] = useState(numericCols[1] ?? numericCols[0] ?? "");
  const [chart, setChart] = useState<ChartData | null>(null);
  const [chartExplain, setChartExplain] = useState<ExplainResponse | null>(null);
  const [overview, setOverview] = useState<ExplainResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [explaining, setExplaining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load EDA summary and an initial chart whenever the data changes.
  useEffect(() => {
    getEdaSummary(datasetId).then(setSummary);
    const initial: ChartSpec =
      numericCols.length >= 2
        ? { type: "correlation_heatmap" }
        : { type: "histogram", column: numericCols[0] ?? allCols[0] };
    render(initial);
    setOverview(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetId, version]);

  function specFor(t: ChartType): ChartSpec {
    switch (t) {
      case "scatter":
      case "line":
        return { type: t, x, y };
      case "correlation_heatmap":
        return { type: t };
      default:
        return { type: t, column };
    }
  }

  async function render(spec: ChartSpec) {
    setBusy(true);
    setError(null);
    setChartExplain(null);
    try {
      setChart(await postChart(datasetId, spec));
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Could not build this chart.");
      setChart(null);
    } finally {
      setBusy(false);
    }
  }

  function loadRecommended(rec: RecommendedChart) {
    setType(rec.type);
    if (rec.column) setColumn(rec.column);
    if (rec.x) setX(rec.x);
    if (rec.y) setY(rec.y);
    render({
      type: rec.type,
      column: rec.column ?? undefined,
      x: rec.x ?? undefined,
      y: rec.y ?? undefined,
    });
  }

  async function onExplainChart() {
    if (!chart) return;
    setExplaining(true);
    try {
      setChartExplain(await explain(datasetId, "chart", specFor(type)));
    } finally {
      setExplaining(false);
    }
  }

  async function onExplainOverview() {
    setOverview(await explain(datasetId, "overview"));
  }

  const needsColumn = ["histogram", "bar", "pie", "box"].includes(type);
  const needsXY = ["scatter", "line"].includes(type);

  return (
    <div className="space-y-6">
      {/* AI overview */}
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-700">AI overview</h3>
          <button
            onClick={onExplainOverview}
            className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500"
          >
            Explain this dataset
          </button>
        </div>
        {overview ? (
          <p className="mt-3 text-sm leading-relaxed text-slate-600">
            {overview.text} <SourceBadge source={overview.source} />
          </p>
        ) : (
          <p className="mt-3 text-sm text-slate-400">
            Get an AI-written summary of the key patterns in this data.
          </p>
        )}
      </div>

      {/* Recommended charts */}
      {summary && summary.recommended_charts.length > 0 && (
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Recommended
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {summary.recommended_charts.map((rec, i) => (
              <button
                key={i}
                onClick={() => loadRecommended(rec)}
                className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 hover:border-indigo-300 hover:text-indigo-700"
                title={rec.reason}
              >
                {CHART_LABELS[rec.type]}
                {rec.column ? `: ${rec.column}` : ""}
                {rec.x ? `: ${rec.x} vs ${rec.y}` : ""}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Builder + chart */}
      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-slate-700">Chart builder</h3>
          <Select
            label="Chart type"
            value={type}
            onChange={(v) => setType(v as ChartType)}
            options={Object.entries(CHART_LABELS).map(([value, label]) => ({
              value,
              label,
            }))}
          />
          {needsColumn && (
            <Select
              label="Column"
              value={column}
              onChange={setColumn}
              options={(type === "histogram" || type === "box"
                ? numericCols
                : allCols
              ).map((c) => ({ value: c, label: c }))}
            />
          )}
          {needsXY && (
            <>
              <Select
                label="X"
                value={x}
                onChange={setX}
                options={(type === "line" ? allCols : numericCols).map((c) => ({
                  value: c,
                  label: c,
                }))}
              />
              <Select
                label="Y"
                value={y}
                onChange={setY}
                options={numericCols.map((c) => ({ value: c, label: c }))}
              />
            </>
          )}
          <button
            onClick={() => render(specFor(type))}
            disabled={busy}
            className="mt-4 w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-60"
          >
            {busy ? "Rendering…" : "Render chart"}
          </button>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5">
          {error && <p className="text-sm text-red-600">{error}</p>}
          {chart ? (
            <>
              <Chart option={buildOption(chart)} />
              <div className="mt-3 flex items-center gap-3">
                <button
                  onClick={onExplainChart}
                  disabled={explaining}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-60"
                >
                  {explaining ? "Explaining…" : "Explain this chart"}
                </button>
              </div>
              {chartExplain && (
                <p className="mt-3 text-sm leading-relaxed text-slate-600">
                  {chartExplain.text} <SourceBadge source={chartExplain.source} />
                </p>
              )}
            </>
          ) : (
            !error && <p className="text-sm text-slate-400">Building chart…</p>
          )}
        </div>
      </div>
    </div>
  );
}

function SourceBadge({ source }: { source: "llm" | "fallback" }) {
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

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <label className="mt-3 block">
      <span className="text-sm font-medium text-slate-600">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
