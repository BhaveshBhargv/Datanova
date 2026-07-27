import { useEffect, useMemo, useState } from "react";
import type { ColumnInfo } from "../lib/datasets";
import {
  createExperiment,
  deleteExperiment,
  listExperiments,
  type Experiment,
} from "../lib/experiments";
import { formatDate } from "../lib/format";
import ExplainabilitySection from "./ExplainabilitySection";

const METRIC_ORDER: Record<string, string[]> = {
  classification: ["accuracy", "precision", "recall", "f1", "roc_auc"],
  regression: ["r2", "rmse", "mae"],
};

export default function ModelsPanel({
  datasetId,
  columns,
  rowCount,
}: {
  datasetId: string;
  columns: ColumnInfo[];
  rowCount: number;
}) {
  const colNames = useMemo(() => columns.map((c) => c.name), [columns]);
  const [target, setTarget] = useState(colNames[colNames.length - 1] ?? "");
  const [excluded, setExcluded] = useState<Set<string>>(new Set());
  const [testSize, setTestSize] = useState(0.2);
  const [running, setRunning] = useState(false);
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [history, setHistory] = useState<Experiment[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setHistory(await listExperiments(datasetId));
  }
  useEffect(() => {
    refresh();
  }, [datasetId]);

  function toggleExclude(name: string) {
    setExcluded((s) => {
      const next = new Set(s);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  }

  async function train() {
    setError(null);
    setRunning(true);
    setExperiment(null);
    try {
      const features = colNames.filter((c) => c !== target && !excluded.has(c));
      const exp = await createExperiment(datasetId, {
        target,
        features,
        test_size: testSize,
      });
      setExperiment(exp);
      await refresh();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Training failed.");
    } finally {
      setRunning(false);
    }
  }

  async function onDelete(id: string) {
    await deleteExperiment(id);
    if (experiment?.id === id) setExperiment(null);
    await refresh();
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
      {/* Config */}
      <div className="card h-fit p-5">
        <p className="eyebrow">AutoML</p>
        <h3 className="mt-1 font-display text-lg font-bold text-ink">Train models</h3>

        <label className="mt-4 block">
          <span className="text-sm font-medium text-slate-600">Target column</span>
          <select
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            className="input mt-1.5"
          >
            {colNames.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>

        <div className="mt-4">
          <span className="text-sm font-medium text-slate-600">Exclude features</span>
          <div className="mt-1.5 max-h-40 space-y-1 overflow-y-auto rounded-lg border border-line p-2">
            {colNames
              .filter((c) => c !== target)
              .map((c) => (
                <label
                  key={c}
                  className="flex items-center gap-2 rounded px-1 py-0.5 text-sm hover:bg-slate-50"
                >
                  <input
                    type="checkbox"
                    checked={excluded.has(c)}
                    onChange={() => toggleExclude(c)}
                    className="accent-nova-600"
                  />
                  {c}
                </label>
              ))}
          </div>
        </div>

        <label className="mt-4 block">
          <span className="text-sm font-medium text-slate-600">
            Test size · <span className="font-mono text-nova-600">{testSize.toFixed(2)}</span>
          </span>
          <input
            type="range"
            min={0.1}
            max={0.5}
            step={0.05}
            value={testSize}
            onChange={(e) => setTestSize(Number(e.target.value))}
            className="mt-2 w-full accent-nova-600"
          />
        </label>

        {error && <p className="mt-3 text-sm text-nova-700">{error}</p>}
        <button
          onClick={train}
          disabled={running || !target}
          className="btn-nova mt-4 w-full disabled:opacity-60"
        >
          {running ? "Training…" : "Train models"}
        </button>

        {history.length > 0 && (
          <div className="mt-6 border-t border-line pt-4">
            <p className="eyebrow">History</p>
            <ul className="mt-2 space-y-1">
              {history.map((h) => (
                <li key={h.id} className="flex items-center justify-between gap-2">
                  <button
                    onClick={() => setExperiment(h)}
                    className={`truncate text-left text-sm hover:text-nova-700 ${
                      experiment?.id === h.id ? "font-medium text-nova-700" : "text-slate-600"
                    }`}
                    title={`${h.target_column} · ${h.problem_type}`}
                  >
                    {h.target_column}{" "}
                    <span className="font-mono text-xs text-slate-400">
                      {h.problem_type}
                    </span>
                  </button>
                  <button
                    onClick={() => onDelete(h.id)}
                    className="text-slate-300 hover:text-red-500"
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Results */}
      <div>
        {running && (
          <div className="card flex items-center gap-3 p-8 text-sm text-slate-500">
            <span className="h-2 w-2 animate-spark-pulse rounded-full bg-nova-500" />
            Detecting the problem type and training the model roster…
          </div>
        )}
        {!running && !experiment && (
          <div className="card p-10 text-center text-sm text-slate-400">
            Choose a target column and train to see a model leaderboard.
          </div>
        )}
        {experiment && <Leaderboard experiment={experiment} />}
        {experiment?.status === "completed" && (
          <ExplainabilitySection
            key={experiment.id}
            experimentId={experiment.id}
            rowCount={rowCount}
          />
        )}
      </div>
    </div>
  );
}

function Leaderboard({ experiment }: { experiment: Experiment }) {
  if (experiment.status === "failed") {
    return (
      <div className="card border-l-4 border-l-red-500 p-5">
        <Meta experiment={experiment} />
        <p className="mt-3 text-sm text-red-600">{experiment.error}</p>
      </div>
    );
  }
  const results = experiment.results ?? [];
  const metricKeys = (METRIC_ORDER[experiment.problem_type] ?? []).filter((k) =>
    results.some((r) => k in r.metrics),
  );
  const primary = experiment.problem_type === "classification" ? "f1" : "r2";
  const best = results.find((r) => r.model === experiment.best_model_name);

  return (
    <div className="card p-5">
      <Meta experiment={experiment} />

      {best && (
        <div className="mt-4 flex items-end justify-between rounded-xl bg-nova-50 px-4 py-3">
          <div>
            <p className="eyebrow text-nova-500">Best model</p>
            <p className="mt-0.5 font-display text-lg font-bold text-ink">
              {best.model}
            </p>
          </div>
          <div className="text-right">
            <div className="font-display text-2xl font-bold tabular-nums text-nova-700">
              {fmt(best.metrics[primary])}
            </div>
            <div className="eyebrow text-nova-500">{primary}</div>
          </div>
        </div>
      )}

      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-line text-left">
              <th className="px-3 py-2 font-mono text-[11px] uppercase tracking-wider text-slate-400">
                Model
              </th>
              {metricKeys.map((k) => (
                <th
                  key={k}
                  className="px-3 py-2 text-right font-mono text-[11px] uppercase tracking-wider text-slate-400"
                >
                  {k}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {results.map((r) => {
              const isBest = r.model === experiment.best_model_name;
              return (
                <tr key={r.model} className={isBest ? "bg-nova-50/50" : ""}>
                  <td className="px-3 py-2.5 font-medium text-ink">
                    {r.model}
                    {isBest && (
                      <span className="ml-2 rounded bg-nova-600 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-white">
                        best
                      </span>
                    )}
                  </td>
                  {metricKeys.map((k) => (
                    <td
                      key={k}
                      className={`px-3 py-2.5 text-right font-mono text-xs ${
                        k === primary ? "font-bold text-ink" : "text-slate-500"
                      }`}
                    >
                      {fmt(r.metrics[k])}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Meta({ experiment }: { experiment: Experiment }) {
  return (
    <div className="flex flex-wrap items-center gap-2 font-mono text-xs text-slate-400">
      <span className="rounded bg-slate-100 px-2 py-0.5 font-medium text-slate-600">
        {experiment.problem_type}
      </span>
      <span>target {experiment.target_column}</span>
      <span>· {experiment.feature_columns.length} features</span>
      <span>· test {experiment.test_size}</span>
      {experiment.completed_at && <span>· {formatDate(experiment.completed_at)}</span>}
    </div>
  );
}

function fmt(v: number | null | string | undefined): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return v.toFixed(4);
  return String(v);
}
