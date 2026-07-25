import { useEffect, useState } from "react";
import { getProfile, type DatasetProfile } from "../lib/profile";
import { formatBytes } from "../lib/format";

function num(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(2);
  return String(v);
}

function scoreColor(score: number): string {
  if (score >= 85) return "text-emerald-600";
  if (score >= 60) return "text-amber-600";
  return "text-red-600";
}

export default function ProfilePanel({
  datasetId,
  version,
}: {
  datasetId: string;
  version: number;
}) {
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getProfile(datasetId)
      .then(setProfile)
      .finally(() => setLoading(false));
  }, [datasetId, version]);

  if (loading) return <p className="text-sm text-slate-500">Analyzing…</p>;
  if (!profile) return <p className="text-sm text-red-600">No profile available.</p>;

  const stats = [
    { label: "Rows", value: profile.n_rows.toLocaleString() },
    { label: "Columns", value: profile.n_columns },
    { label: "Duplicate rows", value: profile.duplicate_rows },
    { label: "Missing cells", value: `${profile.missing_cells} (${profile.missing_pct}%)` },
    { label: "Memory", value: formatBytes(profile.memory_bytes) },
  ];

  return (
    <div>
      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <div className={`text-2xl font-semibold ${scoreColor(profile.quality_score)}`}>
            {profile.quality_score}
          </div>
          <div className="mt-1 text-xs text-slate-500">Quality score</div>
        </div>
        {stats.map((s) => (
          <div key={s.label} className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="text-2xl font-semibold text-slate-900">{s.value}</div>
            <div className="mt-1 text-xs text-slate-500">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Per-column table */}
      <div className="mt-6 overflow-x-auto rounded-xl border border-slate-200 bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-2 font-medium">Column</th>
              <th className="px-4 py-2 font-medium">Type</th>
              <th className="px-4 py-2 font-medium">Missing</th>
              <th className="px-4 py-2 font-medium">Unique</th>
              <th className="px-4 py-2 font-medium">Min</th>
              <th className="px-4 py-2 font-medium">Mean</th>
              <th className="px-4 py-2 font-medium">Max</th>
              <th className="px-4 py-2 font-medium">Outliers</th>
              <th className="px-4 py-2 font-medium">Suggestion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {profile.columns.map((c) => (
              <tr key={c.name} className="hover:bg-slate-50">
                <td className="whitespace-nowrap px-4 py-2 font-medium text-slate-700">
                  {c.name}
                </td>
                <td className="px-4 py-2 text-slate-500">{c.dtype}</td>
                <td className="px-4 py-2">
                  <span className={c.missing > 0 ? "text-amber-600" : "text-slate-500"}>
                    {c.missing} ({c.missing_pct}%)
                  </span>
                </td>
                <td className="px-4 py-2 text-slate-500">{c.unique}</td>
                <td className="px-4 py-2 text-slate-500">{num(c.min)}</td>
                <td className="px-4 py-2 text-slate-500">{num(c.mean)}</td>
                <td className="px-4 py-2 text-slate-500">{num(c.max)}</td>
                <td className="px-4 py-2">
                  <span
                    className={
                      (c.outliers ?? 0) > 0 ? "text-amber-600" : "text-slate-400"
                    }
                  >
                    {c.outliers ?? "—"}
                  </span>
                </td>
                <td className="px-4 py-2">
                  {c.suggested_type ? (
                    <span className="rounded bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
                      → {c.suggested_type}
                    </span>
                  ) : (
                    <span className="text-slate-300">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
