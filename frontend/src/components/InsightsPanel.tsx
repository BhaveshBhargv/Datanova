import { useEffect, useState } from "react";
import {
  getInsights,
  getInsightsNarrative,
  type Insight,
  type InsightsResponse,
  type Severity,
} from "../lib/insights";
import type { ExplainResponse } from "../lib/eda";
import { PanelHeading } from "./ui";

const SEVERITY: Record<
  Severity,
  { rail: string; dot: string; badge: string; label: string; count: string }
> = {
  critical: {
    rail: "border-l-red-500",
    dot: "bg-red-500",
    badge: "bg-red-50 text-red-600",
    label: "Critical",
    count: "text-red-600",
  },
  warning: {
    rail: "border-l-amber-500",
    dot: "bg-amber-500",
    badge: "bg-amber-50 text-amber-700",
    label: "Warning",
    count: "text-amber-600",
  },
  info: {
    rail: "border-l-nova-400",
    dot: "bg-nova-500",
    badge: "bg-nova-50 text-nova-700",
    label: "Info",
    count: "text-nova-600",
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
  if (!data) return <p className="text-sm text-nova-700">No insights available.</p>;

  return (
    <div className="mx-auto max-w-4xl">
      <PanelHeading
        eyebrow="Findings"
        title="Insights & recommendations"
        action={
          <button
            onClick={summarize}
            disabled={narrating || data.total === 0}
            className="btn-nova disabled:opacity-60"
          >
            {narrating ? "Summarizing…" : "AI summary"}
          </button>
        }
      />

      {/* Severity readouts */}
      <div className="grid grid-cols-3 gap-3">
        {(["critical", "warning", "info"] as Severity[]).map((s) => (
          <div key={s} className="card p-4">
            <div className={`font-display text-2xl font-bold tabular-nums ${SEVERITY[s].count}`}>
              {data.counts[s]}
            </div>
            <div className="eyebrow mt-1">{s}</div>
          </div>
        ))}
      </div>

      {narrative && (
        <div className="mt-5 rounded-2xl border border-nova-100 bg-nova-50/50 p-5">
          <p className="eyebrow text-nova-500">Executive summary</p>
          <p className="mt-2 text-sm leading-relaxed text-ink">
            {narrative.text}
            <span
              className={`ml-1 rounded px-1.5 py-0.5 text-xs font-medium ${
                narrative.source === "llm"
                  ? "bg-white text-nova-700"
                  : "bg-slate-100 text-slate-500"
              }`}
            >
              {narrative.source === "llm" ? "AI" : "rule-based"}
            </span>
          </p>
        </div>
      )}

      {/* Insight cards */}
      <div className="mt-6 space-y-3">
        {data.insights.length === 0 ? (
          <div className="card p-8 text-center text-sm text-slate-500">
            No notable issues or patterns were found — this dataset looks clean.
          </div>
        ) : (
          data.insights.map((ins, i) => <InsightCard key={i} insight={ins} />)
        )}
      </div>
    </div>
  );
}

function InsightCard({ insight }: { insight: Insight }) {
  const s = SEVERITY[insight.severity];
  return (
    <div className={`card border-l-4 p-4 ${s.rail}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${s.badge}`}>
          {s.label}
        </span>
        <span className="font-mono text-[11px] uppercase tracking-wider text-slate-400">
          {insight.category.replace("_", " ")}
        </span>
      </div>
      <div className="mt-1.5 font-medium text-ink">{insight.title}</div>
      <p className="mt-1 text-sm text-slate-600">{insight.detail}</p>
      {insight.recommendation && (
        <p className="mt-2 flex items-start gap-1.5 text-sm text-nova-700">
          <span className="mt-0.5 text-nova-400">→</span>
          {insight.recommendation}
        </p>
      )}
    </div>
  );
}
