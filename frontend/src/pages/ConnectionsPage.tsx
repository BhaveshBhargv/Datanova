import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  createConnection,
  deleteConnection,
  importFrom,
  listConnections,
  listTables,
  testConnection,
  type Connection,
  type ConnectionCreate,
  type Dialect,
} from "../lib/connections";
import { formatDate } from "../lib/format";

const DIALECTS: Dialect[] = ["postgresql", "mysql", "sqlite"];
const DEFAULT_PORTS: Record<Dialect, number | undefined> = {
  postgresql: 5432,
  mysql: 3306,
  sqlite: undefined,
};

const emptyForm: ConnectionCreate = {
  name: "",
  dialect: "postgresql",
  database: "",
  host: "",
  port: 5432,
  username: "",
  password: "",
};

export default function ConnectionsPage() {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [form, setForm] = useState<ConnectionCreate>(emptyForm);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function refresh() {
    setConnections(await listConnections());
  }
  useEffect(() => {
    refresh();
  }, []);

  function update<K extends keyof ConnectionCreate>(
    key: K,
    value: ConnectionCreate[K],
  ) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function onDialectChange(dialect: Dialect) {
    setForm((f) => ({ ...f, dialect, port: DEFAULT_PORTS[dialect] ?? null }));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await createConnection(form);
      setForm(emptyForm);
      await refresh();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Could not create connection.");
    } finally {
      setSaving(false);
    }
  }

  const isSqlite = form.dialect === "sqlite";

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-2xl font-semibold text-slate-900">Connections</h1>
      <p className="mt-1 text-sm text-slate-500">
        Connect a SQL database, then import tables or query results as datasets.
      </p>

      {/* Create form */}
      <form
        onSubmit={onSubmit}
        className="mt-6 grid grid-cols-1 gap-4 rounded-xl border border-slate-200 bg-white p-6 sm:grid-cols-2"
      >
        <Input label="Name" value={form.name} onChange={(v) => update("name", v)} />
        <div>
          <span className="text-sm font-medium text-slate-700">Dialect</span>
          <select
            value={form.dialect}
            onChange={(e) => onDialectChange(e.target.value as Dialect)}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
          >
            {DIALECTS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>

        <Input
          label={isSqlite ? "Database file path" : "Database name"}
          value={form.database}
          onChange={(v) => update("database", v)}
        />

        {!isSqlite && (
          <>
            <Input
              label="Host"
              value={form.host ?? ""}
              onChange={(v) => update("host", v)}
            />
            <Input
              label="Port"
              type="number"
              value={form.port?.toString() ?? ""}
              onChange={(v) => update("port", v ? Number(v) : null)}
            />
            <Input
              label="Username"
              value={form.username ?? ""}
              onChange={(v) => update("username", v)}
            />
            <Input
              label="Password"
              type="password"
              value={form.password ?? ""}
              onChange={(v) => update("password", v)}
            />
          </>
        )}

        <div className="sm:col-span-2">
          {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-60"
          >
            {saving ? "Testing & saving…" : "Test & save connection"}
          </button>
        </div>
      </form>

      {/* Connection list */}
      <div className="mt-8 space-y-3">
        {connections.length === 0 ? (
          <p className="text-sm text-slate-500">No connections yet.</p>
        ) : (
          connections.map((c) => (
            <ConnectionCard key={c.id} conn={c} onChanged={refresh} />
          ))
        )}
      </div>
    </div>
  );
}

function Input({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
      />
    </label>
  );
}

function ConnectionCard({
  conn,
  onChanged,
}: {
  conn: Connection;
  onChanged: () => void;
}) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [tables, setTables] = useState<string[] | null>(null);
  const [table, setTable] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onTest() {
    setStatus("Testing…");
    const r = await testConnection(conn.id);
    setStatus(r.message);
  }

  async function onOpen() {
    setOpen((o) => !o);
    if (!tables) {
      try {
        const t = await listTables(conn.id);
        setTables(t);
        setTable(t[0] ?? "");
      } catch (err: any) {
        setStatus(err?.response?.data?.detail ?? "Could not list tables.");
      }
    }
  }

  async function onImport(useQuery: boolean) {
    setBusy(true);
    setStatus(null);
    try {
      const ds = await importFrom(
        conn.id,
        useQuery ? { query } : { table },
      );
      navigate(`/datasets/${ds.id}`);
    } catch (err: any) {
      setStatus(err?.response?.data?.detail ?? "Import failed.");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete() {
    if (!confirm("Delete this connection?")) return;
    await deleteConnection(conn.id);
    onChanged();
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="font-medium text-slate-800">{conn.name}</div>
          <div className="text-xs text-slate-500">
            {conn.dialect}
            {conn.host ? ` · ${conn.host}:${conn.port ?? ""}` : ""} ·{" "}
            {conn.database} · added {formatDate(conn.created_at)}
          </div>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <button onClick={onTest} className="text-slate-500 hover:text-slate-800">
            Test
          </button>
          <button onClick={onOpen} className="text-indigo-600 hover:underline">
            {open ? "Close" : "Browse & import"}
          </button>
          <button onClick={onDelete} className="text-slate-400 hover:text-red-600">
            Delete
          </button>
        </div>
      </div>

      {open && (
        <div className="mt-4 grid gap-4 border-t border-slate-100 pt-4 sm:grid-cols-2">
          <div>
            <span className="text-sm font-medium text-slate-700">Import a table</span>
            <select
              value={table}
              onChange={(e) => setTable(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              {(tables ?? []).map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <button
              onClick={() => onImport(false)}
              disabled={busy || !table}
              className="mt-2 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-60"
            >
              Import table
            </button>
          </div>
          <div>
            <span className="text-sm font-medium text-slate-700">Or run a query</span>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="SELECT * FROM ..."
              rows={3}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
            />
            <button
              onClick={() => onImport(true)}
              disabled={busy || !query.trim()}
              className="mt-2 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-60"
            >
              Import query
            </button>
          </div>
        </div>
      )}

      {status && <p className="mt-3 text-sm text-slate-500">{status}</p>}
    </div>
  );
}
