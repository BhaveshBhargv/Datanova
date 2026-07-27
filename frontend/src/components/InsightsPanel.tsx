import { useEffect, useState } from "react";
import {
  getInsights,
  getInsightsNarrative,
  type Insight,
  type InsightsResponse,
  type Severity,
} from "../lib/insights";
import type { ExplainResponse } from "../lib/eda";

const SEVERITY_STYLES: Record<Severity, { border: string; badge: string; label: string }> = {
  critical: {
    border: "border-l-red-500",
    badge: "bg-red-100 text-red-700",
    label: "Critical",
  },
  warning: {
    border: "border-l-amber-500",
    badge: "bg-amber-100 text-amber-700",
    label: "Warning",
  },
  info: {
    border: "border-l-indigo-400",
    badge: "bg-indigo-100 text-indigo-700",
    label: "Info",
  },
};

export default function InsightsPanel({
  datasetId,
  version,
}: {
  datasetId: string;
  version: number;
}) {
  const [data, setData] = useState<InsightsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [narrative, setNarrative] = useState<ExplainResponse | null>(null);
  const [narrating, setNarrating] = useState(false);

  useEffect(() => {
    setLoading(true);
    setNarrative(null);
    getInsights(datasetId)
      .then(setData)
      .finally(() => setLoading(false));
  }, [datasetId, version]);

  async function summarize() {
    setNarrating(true);
    try {
      setNarrative(await getInsightsNarrative(datasetId));
    } finally {
      setNarrating(false);
    }
  }

  if (loading) return <p className="text-sm text-slate-500">Analyzing…</p>;
  if (!data) return <p className="text-sm text-red-600">No insights available.</p>;

  return (
    <div className="mx-auto max-w-4xl">
      {/* Summary + AI narrative */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2 text-sm">
          <Count n={data.counts.critical} label="critical" cls="bg-red-100 text-red-700" />
          <Count n={data.counts.warning} label="warning" cls="bg-amber-100 text-amber-700" />
          <Count n={data.counts.info} label="info" cls="bg-indigo-100 text-indigo-700" />
        </div>
        <button
          onClick={summarize}
          disabled={narrating || data.total === 0}
          className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-60"
        >
          {narrating ? "Summarizing…" : "AI summary"}
        </button>
      </div>

      {narrative && (
        <p className="mt-4 rounded-xl border border-slate-200 bg-white p-4 text-sm leading-relaxed text-slate-700">
          {narrative.text}
          <span
            className={`ml-1 rounded px-1.5 py-0.5 text-xs font-medium ${
              narrative.source === "llm"
                ? "bg-indigo-50 text-indigo-700"
                : "bg-slate-100 text-slate-500"
            }`}
          >
            {narrative.source === "llm" ? "AI" : "rule-based"}
          </span>
        </p>
      )}

      {/* Insight cards */}
      <div className="mt-6 space-y-3">
        {data.insights.length === 0 ? (
          <p className="text-sm text-slate-500">
            No notable issues or patterns were found in this dataset.
          </p>
        ) : (
          data.insights.map((ins, i) => <InsightCard key={i} insight={ins} />)
        )}
      </div>
    </div>
  );
}

function Count({ n, label, cls }: { n: number; label: string; cls: string }) {
  return (
    <span className={`rounded-lg px-2.5 py-1 font-medium ${cls}`}>
      {n} {label}
    </span>
  );
}

function InsightCard({ insight }: { insight: Insight }) {
  const style = SEVERITY_STYLES[insight.severity];
  return (
    <div className={`rounded-xl border border-l-4 border-slate-200 bg-white p-4 ${style.border}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${style.badge}`}>
          {style.label}
        </span>
        <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500">
          {insight.category.replace("_", " ")}
        </span>
        <span className="font-medium text-slate-800">{insight.title}</span>
      </div>
      <p className="mt-1 text-sm text-slate-600">{insight.detail}</p>
      {insight.recommendation && (
        <p className="mt-1 text-sm text-indigo-700">→ {insight.recommendation}</p>
      )}
    </div>
  );
}
