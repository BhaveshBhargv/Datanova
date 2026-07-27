import type { ReactNode } from "react";

/** Eyebrow + display heading + optional right-aligned action. */
export function PanelHeading({
  eyebrow,
  title,
  action,
}: {
  eyebrow: string;
  title: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h3 className="mt-1 font-display text-xl font-bold text-ink">{title}</h3>
      </div>
      {action}
    </div>
  );
}

/** Instrument-style readout tile. */
export function Stat({
  value,
  label,
  tone = "ink",
}: {
  value: ReactNode;
  label: string;
  tone?: "ink" | "nova" | "amber" | "signal";
}) {
  const color = {
    ink: "text-ink",
    nova: "text-nova-600",
    amber: "text-amber-600",
    signal: "text-signal",
  }[tone];
  return (
    <div className="card p-4">
      <div className={`font-display text-2xl font-bold tabular-nums ${color}`}>
        {value}
      </div>
      <div className="eyebrow mt-1">{label}</div>
    </div>
  );
}

/** Circular gauge for a 0–100 score. */
export function ScoreRing({ value, label }: { value: number; label: string }) {
  const r = 30;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - Math.max(0, Math.min(100, value)) / 100);
  const stroke =
    value >= 85 ? "#0E9E9E" : value >= 60 ? "#F6B01E" : "#C51E8A";
  return (
    <div className="card flex items-center gap-4 p-4">
      <svg width="76" height="76" viewBox="0 0 76 76" className="shrink-0">
        <circle cx="38" cy="38" r={r} fill="none" stroke="#EEF0F4" strokeWidth="8" />
        <circle
          cx="38"
          cy="38"
          r={r}
          fill="none"
          stroke={stroke}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          transform="rotate(-90 38 38)"
        />
        <text
          x="38"
          y="43"
          textAnchor="middle"
          className="fill-ink font-display text-lg font-bold"
        >
          {Math.round(value)}
        </text>
      </svg>
      <div>
        <div className="eyebrow">{label}</div>
        <div className="mt-1 text-sm text-slate-500">
          {value >= 85 ? "Healthy" : value >= 60 ? "Some issues" : "Needs attention"}
        </div>
      </div>
    </div>
  );
}

/** Shared data-table shell with mono headers. */
export function DataTable({
  headers,
  children,
  className = "",
}: {
  headers: ReactNode[];
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`card overflow-x-auto ${className}`}>
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-line text-left">
            {headers.map((h, i) => (
              <th
                key={i}
                className="whitespace-nowrap px-4 py-2.5 font-mono text-[11px] font-normal uppercase tracking-wider text-slate-400"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">{children}</tbody>
      </table>
    </div>
  );
}

export function Pill({
  children,
  tone = "slate",
}: {
  children: ReactNode;
  tone?: "slate" | "nova" | "amber" | "signal" | "red";
}) {
  const tones = {
    slate: "bg-slate-100 text-slate-600",
    nova: "bg-nova-50 text-nova-700",
    amber: "bg-amber-50 text-amber-700",
    signal: "bg-teal-50 text-signal",
    red: "bg-red-50 text-red-600",
  }[tone];
  return (
    <span className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${tones}`}>
      {children}
    </span>
  );
}
