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
        itemStyle: { color: "#C51E8A" },
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
    <div className="card mt-6 p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="eyebrow">Explainable AI</p>
          <h3 className="mt-1 font-display text-lg font-bold text-ink">
            SHAP explanations
          </h3>
        </div>
        {!importance && (
          <button
            onClick={computeImportance}
            disabled={loading}
            className="btn-nova disabled:opacity-60"
          >
            {loading ? "Computing…" : "Compute SHAP"}
          </button>
        )}
      </div>

      {error && <p className="mt-3 text-sm text-nova-700">{error}</p>}

      {importance && (
        <div className="mt-5 space-y-8">
          {/* Global importance */}
          <div>
            <div className="flex items-center justify-between">
              <p className="eyebrow">
                Feature importance · {importance.sample_size} rows
              </p>
              <button
                onClick={narrate}
                disabled={narrating}
                className="btn-ghost !px-3 !py-1.5 text-xs disabled:opacity-60"
              >
                {narrating ? "Explaining…" : "Explain drivers (AI)"}
              </button>
            </div>
            <Chart
              option={importanceOption(importance.importance)}
              height={Math.max(180, importance.importance.length * 40)}
            />
            {narrative && (
              <p className="mt-2 rounded-xl bg-nova-50/60 p-3 text-sm leading-relaxed text-ink">
                {narrative.text} <SourceBadge source={narrative.source} />
              </p>
            )}
          </div>

          {/* Per-prediction explanation */}
          <div className="border-t border-line pt-6">
            <p className="eyebrow">Explain a prediction</p>
            <div className="mt-2 flex items-end gap-3">
              <label className="block">
                <span className="text-xs text-slate-500">
                  Row index · 0–{Math.max(0, rowCount - 1)}
                </span>
                <input
                  type="number"
                  min={0}
                  max={rowCount - 1}
                  value={index}
                  onChange={(e) => setIndex(Number(e.target.value))}
                  className="input mt-1 w-28 font-mono"
                />
              </label>
              <button
                onClick={explainRow}
                disabled={busyRow}
                className="btn-nova disabled:opacity-60"
              >
                {busyRow ? "Explaining…" : "Explain row"}
              </button>
            </div>

            {prediction && (
              <div className="mt-4">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="eyebrow">Prediction</span>
                  <span className="rounded bg-nova-600 px-2 py-0.5 font-mono text-xs font-medium text-white">
                    {cellText(prediction.predicted_label ?? prediction.prediction)}
                  </span>
                  {prediction.proba && (
                    <span className="font-mono text-xs text-slate-500">
                      {Object.entries(prediction.proba)
                        .map(([k, v]) => `${k} ${(v * 100).toFixed(0)}%`)
                        .join(" · ")}
                    </span>
                  )}
                  <span className="font-mono text-xs text-slate-400">
                    base {prediction.base_value.toFixed(3)}
                  </span>
                </div>
                <Chart
                  option={contributionsOption(prediction.contributions)}
                  height={Math.max(180, prediction.contributions.length * 40)}
                />
                <div className="mt-1 flex items-center gap-3 font-mono text-[11px] text-slate-400">
                  <span className="flex items-center gap-1">
                    <span className="h-2 w-2 rounded-sm bg-emerald-500" /> pushes up
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="h-2 w-2 rounded-sm bg-red-500" /> pushes down
                  </span>
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
          ? "bg-white text-nova-700"
          : "bg-slate-100 text-slate-500"
      }`}
    >
      {source === "llm" ? "AI" : "rule-based"}
    </span>
  );
}
