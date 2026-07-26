import { useEffect, useMemo, useState } from "react";
import type { ColumnInfo } from "../lib/datasets";
import {
  createExperiment,
  deleteExperiment,
  listExperiments,
  type Experiment,
} from "../lib/experiments";
import { formatDate } from "../lib/format";

const METRIC_ORDER: Record<string, string[]> = {
  classification: ["accuracy", "precision", "recall", "f1", "roc_auc"],
  regression: ["r2", "rmse", "mae"],
};

export default function ModelsPanel({
  datasetId,
  columns,
}: {
  datasetId: string;
  columns: ColumnInfo[];
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
    <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
      {/* Config */}
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="text-sm font-semibold text-slate-700">Train models</h3>

        <label className="mt-4 block">
          <span className="text-sm font-medium text-slate-600">Target column</span>
          <select
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            {colNames.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>

        <div className="mt-4">
          <span className="text-sm font-medium text-slate-600">
            Exclude features
          </span>
          <div className="mt-1 max-h-40 space-y-1 overflow-y-auto rounded-lg border border-slate-200 p-2">
            {colNames
              .filter((c) => c !== target)
              .map((c) => (
                <label key={c} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={excluded.has(c)}
                    onChange={() => toggleExclude(c)}
                  />
                  {c}
                </label>
              ))}
          </div>
        </div>

        <label className="mt-4 block">
          <span className="text-sm font-medium text-slate-600">
            Test size: {testSize.toFixed(2)}
          </span>
          <input
            type="range"
            min={0.1}
            max={0.5}
            step={0.05}
            value={testSize}
            onChange={(e) => setTestSize(Number(e.target.value))}
            className="mt-1 w-full"
          />
        </label>

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        <button
          onClick={train}
          disabled={running || !target}
          className="mt-4 w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-60"
        >
          {running ? "Training models…" : "Train models"}
        </button>

        {history.length > 0 && (
          <div className="mt-6">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              History
            </div>
            <ul className="mt-2 space-y-1 text-sm">
              {history.map((h) => (
                <li key={h.id} className="flex items-center justify-between gap-2">
                  <button
                    onClick={() => setExperiment(h)}
                    className="truncate text-left text-indigo-600 hover:underline"
                    title={`${h.target_column} · ${h.problem_type}`}
                  >
                    {h.target_column} ({h.problem_type})
                  </button>
                  <button
                    onClick={() => onDelete(h.id)}
                    className="text-slate-400 hover:text-red-600"
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
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        {running && (
          <p className="text-sm text-slate-500">
            Detecting the problem type and training the model roster…
          </p>
        )}
        {!running && !experiment && (
          <p className="text-sm text-slate-400">
            Choose a target column and train to see a model leaderboard.
          </p>
        )}
        {experiment && <Leaderboard experiment={experiment} />}
      </div>
    </div>
  );
}

function Leaderboard({ experiment }: { experiment: Experiment }) {
  if (experiment.status === "failed") {
    return (
      <div>
        <Badge experiment={experiment} />
        <p className="mt-3 text-sm text-red-600">{experiment.error}</p>
      </div>
    );
  }
  const results = experiment.results ?? [];
  const metricKeys = (METRIC_ORDER[experiment.problem_type] ?? []).filter((k) =>
    results.some((r) => k in r.metrics),
  );

  return (
    <div>
      <Badge experiment={experiment} />
      <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-2 font-medium">Model</th>
              {metricKeys.map((k) => (
                <th key={k} className="px-4 py-2 font-medium">
                  {k}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {results.map((r) => {
              const isBest = r.model === experiment.best_model_name;
              return (
                <tr key={r.model} className={isBest ? "bg-indigo-50" : ""}>
                  <td className="px-4 py-2 font-medium text-slate-800">
                    {r.model}
                    {isBest && (
                      <span className="ml-2 rounded bg-indigo-600 px-1.5 py-0.5 text-xs text-white">
                        best
                      </span>
                    )}
                  </td>
                  {metricKeys.map((k) => (
                    <td key={k} className="px-4 py-2 text-slate-600">
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

function Badge({ experiment }: { experiment: Experiment }) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <span className="rounded bg-slate-100 px-2 py-0.5 font-medium text-slate-700">
        {experiment.problem_type}
      </span>
      <span className="text-slate-500">
        target: <span className="font-medium">{experiment.target_column}</span>
      </span>
      <span className="text-slate-400">·</span>
      <span className="text-slate-500">
        {experiment.feature_columns.length} features · test {experiment.test_size}
      </span>
      {experiment.completed_at && (
        <span className="text-slate-400">
          · {formatDate(experiment.completed_at)}
        </span>
      )}
    </div>
  );
}

function fmt(v: number | null | string | undefined): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return v.toFixed(4);
  return String(v);
}
