import { useAuth } from "../context/AuthContext";

export default function Dashboard() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <span className="font-semibold text-slate-900">
            AI Analytics Platform
          </span>
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-500">{user?.email}</span>
            <button
              onClick={logout}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              Log out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-10">
        <h1 className="text-2xl font-semibold text-slate-900">
          Welcome{user?.full_name ? `, ${user.full_name}` : ""}.
        </h1>
        <p className="mt-2 text-slate-600">
          You're authenticated. This protected dashboard is the foundation for the
          upcoming phases — dataset ingestion, profiling, EDA, the AI assistant,
          AutoML, and reporting.
        </p>

        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[
            "Upload dataset",
            "Connect database",
            "Explore & visualize",
            "Chat with your data",
            "Train models (AutoML)",
            "Generate report",
          ].map((label) => (
            <div
              key={label}
              className="rounded-xl border border-dashed border-slate-300 bg-white p-5 text-slate-400"
            >
              <div className="font-medium text-slate-700">{label}</div>
              <div className="mt-1 text-xs">Coming in a later phase</div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
