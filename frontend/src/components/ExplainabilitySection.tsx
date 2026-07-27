import { useState } from "react";
import type { EChartsOption } from "echarts";
import {
  explainPrediction,
  getDriverNarrative,
  getImportance,
  type Contribution,
  type FeatureImportance,
  type ImportanceResponse,
  type PredictionExplanation,
} from "../lib/explain";
import type { ExplainResponse } from "../lib/eda";
import { cellText } from "../lib/format";
import Chart from "./Chart";

function importanceOption(importance: FeatureImportance[]): EChartsOption {
  // Reverse so the most important feature sits at the top.
  const rows = [...importance].reverse();
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 130, right: 24, top: 10, bottom: 30 },
    xAxis: { type: "value", name: "mean |SHAP|" },
    yAxis: { type: "category", data: rows.map((r) => r.feature) },
    series: [
      {
        type: "bar",
        data: rows.map((r) => r.importance),
        itemStyle: { color: "#4f46e5" },
      },
    ],
  };
}

function contributionsOption(contributions: Contribution[]): EChartsOption {
  const rows = [...contributions].reverse();
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 130, right: 24, top: 10, bottom: 30 },
    xAxis: { type: "value", name: "SHAP contribution" },
    yAxis: { type: "category", data: rows.map((r) => r.feature) },
    series: [
      {
        type: "bar",
        data: rows.map((r) => ({
          value: r.contribution,
          itemStyle: { color: r.contribution >= 0 ? "#16a34a" : "#ef4444" },
        })),
      },
    ],
  };
}

export default function ExplainabilitySection({
  experimentId,
  rowCount,
}: {
  experimentId: string;
  rowCount: number;
}) {
  const [importance, setImportance] = useState<ImportanceResponse | null>(null);
  const [narrative, setNarrative] = useState<ExplainResponse | null>(null);
  const [index, setIndex] = useState(0);
  const [prediction, setPrediction] = useState<PredictionExplanation | null>(null);
  const [loading, setLoading] = useState(false);
  const [busyRow, setBusyRow] = useState(false);
  const [narrating, setNarrating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function computeImportance() {
    setLoading(true);
    setError(null);
    try {
      setImportance(await getImportance(experimentId));
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Could not compute SHAP values.");
    } finally {
      setLoading(false);
    }
  }

  async function explainRow() {
    setBusyRow(true);
    setError(null);
    try {
      setPrediction(await explainPrediction(experimentId, index));
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Could not explain this row.");
    } finally {
      setBusyRow(false);
    }
  }

  async function narrate() {
    setNarrating(true);
    try {
      setNarrative(await getDriverNarrative(experimentId));
    } finally {
      setNarrating(false);
    }
  }

  return (
    <div className="mt-6 border-t border-slate-200 pt-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-700">
          Explainability (SHAP)
        </h3>
        {!importance && (
          <button
            onClick={computeImportance}
            disabled={loading}
            className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-60"
          >
            {loading ? "Computing…" : "Compute SHAP explanations"}
          </button>
        )}
      </div>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      {importance && (
        <div className="mt-4 space-y-6">
          {/* Global importance */}
          <div>
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium text-slate-600">
                Global feature importance
              </h4>
              <button
                onClick={narrate}
                disabled={narrating}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-60"
              >
                {narrating ? "Explaining…" : "Explain drivers (AI)"}
              </button>
            </div>
            <div className="mt-1 text-xs text-slate-400">
              Computed on {importance.sample_size} rows
            </div>
            <Chart
              option={importanceOption(importance.importance)}
              height={Math.max(180, importance.importance.length * 40)}
            />
            {narrative && (
              <p className="mt-2 text-sm leading-relaxed text-slate-600">
                {narrative.text} <SourceBadge source={narrative.source} />
              </p>
            )}
          </div>

          {/* Per-prediction explanation */}
          <div>
            <h4 className="text-sm font-medium text-slate-600">
              Explain a prediction
            </h4>
            <div className="mt-2 flex items-end gap-3">
              <label className="block">
                <span className="text-xs text-slate-500">
                  Row index (0–{Math.max(0, rowCount - 1)})
                </span>
                <input
                  type="number"
                  min={0}
                  max={rowCount - 1}
                  value={index}
                  onChange={(e) => setIndex(Number(e.target.value))}
                  className="mt-1 w-28 rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
                />
              </label>
              <button
                onClick={explainRow}
                disabled={busyRow}
                className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-60"
              >
                {busyRow ? "Explaining…" : "Explain row"}
              </button>
            </div>

            {prediction && (
              <div className="mt-4">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="text-slate-500">Prediction:</span>
                  <span className="rounded bg-indigo-600 px-2 py-0.5 font-medium text-white">
                    {cellText(prediction.predicted_label ?? prediction.prediction)}
                  </span>
                  {prediction.proba && (
                    <span className="text-xs text-slate-500">
                      {Object.entries(prediction.proba)
                        .map(([k, v]) => `${k}: ${(v * 100).toFixed(0)}%`)
                        .join(" · ")}
                    </span>
                  )}
                  <span className="text-xs text-slate-400">
                    base {prediction.base_value.toFixed(3)}
                  </span>
                </div>
                <Chart
                  option={contributionsOption(prediction.contributions)}
                  height={Math.max(180, prediction.contributions.length * 40)}
                />
                <div className="mt-1 text-xs text-slate-400">
                  Green pushes the prediction up, red pushes it down.
                </div>
              </div>
            )}
          </div>
        </div>
      )}
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
