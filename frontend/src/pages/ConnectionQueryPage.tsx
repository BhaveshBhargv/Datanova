import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { listConnections, type Connection } from "../lib/connections";
import {
  getSchema,
  listQueries,
  queryConnection,
  type NLQueryResponse,
  type QueryHistoryItem,
  type SchemaTable,
} from "../lib/nlsql";
import { cellText } from "../lib/format";

export default function ConnectionQueryPage() {
  const { id } = useParams<{ id: string }>();
  const [connection, setConnection] = useState<Connection | null>(null);
  const [schema, setSchema] = useState<SchemaTable[]>([]);
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<NLQueryResponse | null>(null);
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [schemaError, setSchemaError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    listConnections().then((cs) =>
      setConnection(cs.find((c) => c.id === id) ?? null),
    );
    getSchema(id)
      .then(setSchema)
      .catch(() => setSchemaError("Could not read the database schema."));
    refreshHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function refreshHistory() {
    if (id) setHistory(await listQueries(id));
  }

  async function ask(text: string) {
    if (!id || !text.trim() || busy) return;
    setBusy(true);
    setResult(null);
    try {
      const res = await queryConnection(id, text);
      setResult(res);
      await refreshHistory();
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    ask(question);
  }

  return (
    <div className="mx-auto max-w-6xl">
      <Link to="/connections" className="text-sm text-indigo-600 hover:underline">
        ← Connections
      </Link>
      <h1 className="mt-3 text-2xl font-semibold text-slate-900">
        Query with AI
        {connection && (
          <span className="ml-2 text-base font-normal text-slate-500">
            {connection.name} · {connection.dialect}
          </span>
        )}
      </h1>

      <div className="mt-6 grid gap-6 lg:grid-cols-[240px_1fr]">
        {/* Schema sidebar */}
        <aside className="rounded-xl border border-slate-200 bg-white p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Schema
          </div>
          {schemaError ? (
            <p className="mt-2 text-sm text-red-600">{schemaError}</p>
          ) : (
            <div className="mt-2 max-h-[70vh] space-y-3 overflow-y-auto">
              {schema.map((t) => (
                <details key={t.table} className="text-sm">
                  <summary className="cursor-pointer font-medium text-slate-700">
                    {t.table}
                  </summary>
                  <ul className="ml-3 mt-1 space-y-0.5 text-xs text-slate-500">
                    {t.columns.map((c) => (
                      <li key={c.name}>
                        {c.name}{" "}
                        <span className="text-slate-400">{c.type}</span>
                      </li>
                    ))}
                  </ul>
                </details>
              ))}
            </div>
          )}
        </aside>

        {/* Console */}
        <div className="space-y-4">
          <form onSubmit={onSubmit} className="flex gap-2">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question about this database…"
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
            />
            <button
              type="submit"
              disabled={busy || !question.trim()}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {busy ? "Running…" : "Ask"}
            </button>
          </form>

          {result && <QueryResult result={result} />}

          {/* History */}
          {history.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Recent queries
              </div>
              <ul className="mt-2 space-y-1 text-sm">
                {history.map((h) => (
                  <li key={h.id}>
                    <button
                      onClick={() => {
                        setQuestion(h.question);
                        ask(h.question);
                      }}
                      className="text-left text-indigo-600 hover:underline"
                    >
                      {h.question}
                    </button>
                    {h.error && (
                      <span className="ml-2 text-xs text-amber-600">(failed)</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function QueryResult({ result }: { result: NLQueryResponse }) {
  return (
    <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-5">
      <p className="text-sm leading-relaxed text-slate-800">
        {result.explanation}
        {result.source && (
          <span
            className={`ml-1 rounded px-1.5 py-0.5 text-xs font-medium ${
              result.source === "llm"
                ? "bg-indigo-50 text-indigo-700"
                : "bg-slate-100 text-slate-500"
            }`}
          >
            {result.source === "llm" ? "AI" : "rule-based"}
          </span>
        )}
      </p>

      {result.error && !result.rows && (
        <p className="text-sm text-amber-600">
          {result.error === "llm_disabled" ? "" : `Note: ${result.error}`}
        </p>
      )}

      {result.sql && (
        <details className="rounded-lg border border-slate-200">
          <summary className="cursor-pointer px-3 py-1.5 text-xs font-medium text-slate-500">
            View SQL
          </summary>
          <pre className="overflow-x-auto px-3 pb-3 text-xs text-slate-700">
            {result.sql}
          </pre>
        </details>
      )}

      {result.optimization_notes.length > 0 && (
        <div className="rounded-lg bg-amber-50 p-3 text-xs text-amber-700">
          <div className="font-medium">Optimization notes</div>
          <ul className="mt-1 list-disc pl-4">
            {result.optimization_notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </div>
      )}

      {result.columns && result.rows && (
        <div className="max-h-72 overflow-auto rounded-lg border border-slate-200">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                {result.columns.map((c) => (
                  <th key={c} className="whitespace-nowrap px-3 py-1.5 font-medium">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {result.rows.slice(0, 200).map((row, i) => (
                <tr key={i}>
                  {result.columns!.map((c) => (
                    <td
                      key={c}
                      className="whitespace-nowrap px-3 py-1.5 text-slate-700"
                    >
                      {cellText(row[c])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {result.plan.length > 0 && (
        <details className="rounded-lg border border-slate-200">
          <summary className="cursor-pointer px-3 py-1.5 text-xs font-medium text-slate-500">
            Query plan (EXPLAIN)
          </summary>
          <pre className="overflow-x-auto px-3 pb-3 text-xs text-slate-600">
            {result.plan.join("\n")}
          </pre>
        </details>
      )}
    </div>
  );
}
