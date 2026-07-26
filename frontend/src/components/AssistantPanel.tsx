import { useEffect, useRef, useState } from "react";
import type { ColumnInfo } from "../lib/datasets";
import {
  getOrCreateConversation,
  postMessage,
  type AssistantMessage,
} from "../lib/assistant";
import { cellText } from "../lib/format";
import { buildOption } from "../lib/echartsOption";
import type { ChartData } from "../lib/eda";
import Chart from "./Chart";

const NUMERIC = new Set(["integer", "float"]);

export default function AssistantPanel({
  datasetId,
  columns,
}: {
  datasetId: string;
  columns: ColumnInfo[];
}) {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getOrCreateConversation(datasetId).then((conv) => {
      setConversationId(conv.id);
      setMessages(conv.messages);
    });
  }, [datasetId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  const suggestions = buildSuggestions(columns);

  async function send(text: string) {
    if (!conversationId || !text.trim() || busy) return;
    setInput("");
    // Optimistically show the user's message.
    setMessages((m) => [
      ...m,
      {
        id: `tmp-${Date.now()}`,
        role: "user",
        content: text,
        created_at: new Date().toISOString(),
      },
    ]);
    setBusy(true);
    try {
      const reply = await postMessage(conversationId, text);
      setMessages((m) => [...m, reply]);
    } catch {
      setMessages((m) => [
        ...m,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          content: "Something went wrong answering that question.",
          error: "request_failed",
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-320px)] min-h-[420px] max-w-3xl flex-col rounded-xl border border-slate-200 bg-white">
      <div className="flex-1 space-y-4 overflow-y-auto p-5">
        {messages.length === 0 && (
          <div className="text-sm text-slate-500">
            <p>Ask a question about this dataset in plain English.</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:border-indigo-300 hover:text-indigo-700"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}

        {busy && (
          <div className="text-sm text-slate-400">The assistant is thinking…</div>
        )}
        <div ref={endRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex gap-2 border-t border-slate-200 p-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about your data…"
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}

function MessageBubble({ message }: { message: AssistantMessage }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl bg-indigo-600 px-4 py-2 text-sm text-white">
          {message.content}
        </div>
      </div>
    );
  }

  const chart = message.result_rows && message.result_columns
    ? chartFor(message.result_columns, message.result_rows)
    : null;

  return (
    <div className="flex justify-start">
      <div className="max-w-[92%] space-y-3">
        <div className="rounded-2xl bg-slate-100 px-4 py-2 text-sm text-slate-800">
          {message.content}
        </div>

        {message.error && !message.result_rows && (
          <div className="text-xs text-amber-600">
            {message.error === "llm_disabled" ? "" : `Note: ${message.error}`}
          </div>
        )}

        {message.sql && (
          <details className="rounded-lg border border-slate-200 bg-white">
            <summary className="cursor-pointer px-3 py-1.5 text-xs font-medium text-slate-500">
              View SQL
            </summary>
            <pre className="overflow-x-auto px-3 pb-3 text-xs text-slate-700">
              {message.sql}
            </pre>
          </details>
        )}

        {chart && <Chart option={buildOption(chart)} height={280} />}

        {message.result_columns && message.result_rows && (
          <ResultTable
            columns={message.result_columns}
            rows={message.result_rows}
          />
        )}
      </div>
    </div>
  );
}

function ResultTable({
  columns,
  rows,
}: {
  columns: string[];
  rows: Record<string, unknown>[];
}) {
  if (rows.length === 0) {
    return <div className="text-xs text-slate-400">No rows returned.</div>;
  }
  return (
    <div className="max-h-64 overflow-auto rounded-lg border border-slate-200">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
          <tr>
            {columns.map((c) => (
              <th key={c} className="whitespace-nowrap px-3 py-1.5 font-medium">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.slice(0, 100).map((row, i) => (
            <tr key={i}>
              {columns.map((c) => (
                <td key={c} className="whitespace-nowrap px-3 py-1.5 text-slate-700">
                  {cellText(row[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Build a bar chart from a 2-column result where one column is numeric. */
function chartFor(
  columns: string[],
  rows: Record<string, unknown>[],
): ChartData | null {
  if (columns.length !== 2 || rows.length === 0 || rows.length > 30) return null;
  const [a, b] = columns;
  const bNumeric = rows.every((r) => typeof r[b] === "number");
  const aNumeric = rows.every((r) => typeof r[a] === "number");
  if (!bNumeric || aNumeric) return null;
  return {
    type: "bar",
    title: `${b} by ${a}`,
    x_label: a,
    y_label: b,
    categories: rows.map((r) => String(r[a])),
    series: [{ name: b, data: rows.map((r) => Number(r[b])) }],
    extra: {},
  };
}

function buildSuggestions(columns: ColumnInfo[]): string[] {
  const numeric = columns.filter((c) => NUMERIC.has(c.dtype)).map((c) => c.name);
  const categorical = columns
    .filter((c) => !NUMERIC.has(c.dtype))
    .map((c) => c.name);
  const out = ["How many rows are there?"];
  if (numeric[0]) out.push(`What is the average ${numeric[0]}?`);
  if (categorical[0] && numeric[0])
    out.push(`Show ${numeric[0]} by ${categorical[0]}.`);
  else if (categorical[0])
    out.push(`What are the most common ${categorical[0]} values?`);
  return out;
}
