import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getWorkspaceSummary, type WorkspaceSummary } from "../lib/workspace";
import { NovaMark } from "../components/brand/NovaMark";
import { formatDate } from "../lib/format";

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState<WorkspaceSummary | null>(null);

  useEffect(() => {
    getWorkspaceSummary().then(setData);
  }, []);

  const firstName = user?.full_name?.split(" ")[0];
  const c = data?.counts ?? { datasets: 0, connections: 0, models: 0, chats: 0 };
  const gauges = [
    { value: c.datasets, label: "datasets" },
    { value: c.models, label: "models" },
    { value: c.connections, label: "connections" },
    { value: c.chats, label: "AI chats" },
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      {/* Observatory hero */}
      <section className="nebula relative overflow-hidden rounded-2xl p-8 text-white shadow-nova">
        <div className="starfield absolute inset-0 opacity-60" />
        <div className="relative">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="eyebrow text-nova-200">Observatory · Workspace</p>
              <h1 className="mt-2 font-display text-3xl font-bold sm:text-4xl">
                Welcome back{firstName ? `, ${firstName}` : ""}.
              </h1>
              <p className="mt-2 max-w-lg text-sm leading-relaxed text-white/70">
                Your datasets, models, and analyses — all in one console. Pick up
                where you left off, or start something new.
              </p>
            </div>
            <NovaMark size={46} animate className="hidden shrink-0 sm:block" />
          </div>

          <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {gauges.map((g) => (
              <div key={g.label} className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
                <div className="font-display text-3xl font-bold tabular-nums">{g.value}</div>
                <div className="mt-1 font-mono text-[11px] uppercase tracking-wider text-white/50">
                  {g.label}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              to="/datasets"
              className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-ink transition hover:bg-white/90"
            >
              Upload a dataset
            </Link>
            <Link
              to="/connections"
              className="rounded-lg border border-white/20 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/10"
            >
              Connect a database
            </Link>
          </div>
        </div>
      </section>

      {/* Recent datasets */}
      <section>
        <SectionHeader
          eyebrow="Data"
          title="Recent datasets"
          action={<Link to="/datasets" className="text-sm font-medium text-nova-600 hover:underline">View all →</Link>}
        />
        {data && data.recent_datasets.length === 0 ? (
          <EmptyState
            title="No datasets yet"
            body="Upload a CSV or Excel file, or import from a database connection."
            to="/datasets"
            cta="Add your first dataset"
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data?.recent_datasets.map((d) => (
              <Link
                key={d.id}
                to={`/datasets/${d.id}`}
                className="card group p-5 transition hover:border-nova-300 hover:shadow-nova"
              >
                <div className="flex items-center justify-between">
                  <span className="eyebrow">
                    {d.source_type === "upload" ? "Upload" : "Database"}
                  </span>
                  <span className="font-mono text-[11px] text-slate-400">
                    {d.n_columns} cols
                  </span>
                </div>
                <div className="mt-2 font-display text-lg font-semibold text-ink group-hover:text-nova-700">
                  {d.name}
                </div>
                <div className="mt-1 font-mono text-xs text-slate-400">
                  {d.n_rows.toLocaleString()} rows · {formatDate(d.created_at)}
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Models + AI queries */}
      <div className="grid gap-6 lg:grid-cols-2">
        <section>
          <SectionHeader eyebrow="Machine learning" title="Recent models" />
          <div className="card divide-y divide-line">
            {data && data.recent_models.length === 0 ? (
              <p className="p-5 text-sm text-slate-500">
                Train a model from any dataset's <b>Models</b> tab.
              </p>
            ) : (
              data?.recent_models.map((m) => (
                <Link
                  key={m.id}
                  to={`/datasets/${m.dataset_id}`}
                  className="flex items-center justify-between gap-3 p-4 hover:bg-slate-50"
                >
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-ink">
                      {m.best_model_name} · {m.dataset_name}
                    </div>
                    <div className="font-mono text-[11px] text-slate-400">
                      predicts {m.target} · {m.problem_type}
                    </div>
                  </div>
                  <span className="text-nova-500">→</span>
                </Link>
              ))
            )}
          </div>
        </section>

        <section>
          <SectionHeader eyebrow="Natural language" title="Recent AI queries" />
          <div className="card divide-y divide-line">
            {data && data.recent_queries.length === 0 ? (
              <p className="p-5 text-sm text-slate-500">
                Ask a connected database questions from <b>Query with AI</b>.
              </p>
            ) : (
              data?.recent_queries.map((q) => (
                <Link
                  key={q.id}
                  to={`/connections/${q.connection_id}/query`}
                  className="block p-4 hover:bg-slate-50"
                >
                  <div className="truncate text-sm text-ink">{q.question}</div>
                  <div className="font-mono text-[11px] text-slate-400">
                    {q.connection_name} · {formatDate(q.created_at)}
                  </div>
                </Link>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function SectionHeader({
  eyebrow,
  title,
  action,
}: {
  eyebrow: string;
  title: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-3 flex items-end justify-between">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2 className="mt-1 font-display text-xl font-bold text-ink">{title}</h2>
      </div>
      {action}
    </div>
  );
}

function EmptyState({
  title,
  body,
  to,
  cta,
}: {
  title: string;
  body: string;
  to: string;
  cta: string;
}) {
  return (
    <div className="card flex flex-col items-center gap-3 p-10 text-center">
      <NovaMark size={30} />
      <div className="font-display text-lg font-semibold text-ink">{title}</div>
      <p className="max-w-sm text-sm text-slate-500">{body}</p>
      <Link to={to} className="btn-nova mt-1">
        {cta}
      </Link>
    </div>
  );
}
