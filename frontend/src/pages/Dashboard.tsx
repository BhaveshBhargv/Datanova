import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { listDatasets } from "../lib/datasets";
import { listConnections } from "../lib/connections";

export default function Dashboard() {
  const { user } = useAuth();
  const [counts, setCounts] = useState({ datasets: 0, connections: 0 });

  useEffect(() => {
    (async () => {
      const [datasets, connections] = await Promise.all([
        listDatasets(),
        listConnections(),
      ]);
      setCounts({ datasets: datasets.length, connections: connections.length });
    })();
  }, []);

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-2xl font-semibold text-slate-900">
        Welcome{user?.full_name ? `, ${user.full_name}` : ""}.
      </h1>
      <p className="mt-1 text-sm text-slate-500">
        Ingest data to get started. Profiling, EDA, the AI assistant, AutoML, and
        reporting arrive in later phases.
      </p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <Link
          to="/datasets"
          className="rounded-xl border border-slate-200 bg-white p-6 transition hover:border-indigo-300 hover:shadow-sm"
        >
          <div className="text-3xl font-semibold text-slate-900">
            {counts.datasets}
          </div>
          <div className="mt-1 font-medium text-slate-700">Datasets</div>
          <div className="mt-1 text-sm text-indigo-600">Upload or import →</div>
        </Link>
        <Link
          to="/connections"
          className="rounded-xl border border-slate-200 bg-white p-6 transition hover:border-indigo-300 hover:shadow-sm"
        >
          <div className="text-3xl font-semibold text-slate-900">
            {counts.connections}
          </div>
          <div className="mt-1 font-medium text-slate-700">Connections</div>
          <div className="mt-1 text-sm text-indigo-600">Connect a database →</div>
        </Link>
      </div>
    </div>
  );
}
