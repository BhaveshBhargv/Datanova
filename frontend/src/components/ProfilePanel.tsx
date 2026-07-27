import { useEffect, useState } from "react";
import { getProfile, type DatasetProfile } from "../lib/profile";
import { formatBytes } from "../lib/format";
import { DataTable, PanelHeading, Pill, ScoreRing, Stat } from "./ui";

function num(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(2);
  return String(v);
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
  if (!profile) return <p className="text-sm text-nova-700">No profile available.</p>;

  return (
    <div>
      <PanelHeading eyebrow="Data quality" title="Profile" />

      {/* Score ring + readouts */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <ScoreRing value={profile.quality_score} label="Quality score" />
        <Stat value={profile.n_rows.toLocaleString()} label="Rows" />
        <Stat value={profile.n_columns} label="Columns" />
        <div className="grid grid-cols-2 gap-3">
          <Stat
            value={profile.duplicate_rows}
            label="Duplicates"
            tone={profile.duplicate_rows > 0 ? "amber" : "ink"}
          />
          <Stat
            value={`${profile.missing_pct}%`}
            label="Missing"
            tone={profile.missing_pct > 0 ? "amber" : "ink"}
          />
        </div>
      </div>

      {/* Per-column table */}
      <p className="eyebrow mb-2 mt-8">Columns · {formatBytes(profile.memory_bytes)}</p>
      <DataTable
        headers={[
          "Column",
          "Type",
          "Missing",
          "Unique",
          "Min",
          "Mean",
          "Max",
          "Outliers",
          "Suggestion",
        ]}
      >
        {profile.columns.map((c) => (
          <tr key={c.name} className="hover:bg-slate-50">
            <td className="whitespace-nowrap px-4 py-2.5 font-medium text-ink">
              {c.name}
            </td>
            <td className="px-4 py-2.5">
              <span className="font-mono text-xs text-slate-500">{c.dtype}</span>
            </td>
            <td className="px-4 py-2.5">
              <div className="flex items-center gap-2">
                <div className="h-1.5 w-14 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={`h-full ${c.missing_pct > 0 ? "bg-amber-400" : "bg-slate-200"}`}
                    style={{ width: `${Math.min(100, c.missing_pct)}%` }}
                  />
                </div>
                <span className="font-mono text-xs text-slate-500">{c.missing_pct}%</span>
              </div>
            </td>
            <td className="px-4 py-2.5 font-mono text-xs text-slate-500">{c.unique}</td>
            <td className="px-4 py-2.5 font-mono text-xs text-slate-500">{num(c.min)}</td>
            <td className="px-4 py-2.5 font-mono text-xs text-slate-500">{num(c.mean)}</td>
            <td className="px-4 py-2.5 font-mono text-xs text-slate-500">{num(c.max)}</td>
            <td className="px-4 py-2.5">
              {(c.outliers ?? 0) > 0 ? (
                <Pill tone="amber">{c.outliers}</Pill>
              ) : (
                <span className="text-slate-300">—</span>
              )}
            </td>
            <td className="px-4 py-2.5">
              {c.suggested_type ? (
                <Pill tone="nova">→ {c.suggested_type}</Pill>
              ) : (
                <span className="text-slate-300">—</span>
              )}
            </td>
          </tr>
        ))}
      </DataTable>
    </div>
  );
}
