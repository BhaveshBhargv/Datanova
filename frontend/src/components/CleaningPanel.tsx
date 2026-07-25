import { useEffect, useMemo, useState } from "react";
import type { ColumnInfo, Dataset } from "../lib/datasets";
import {
  applyTransformation,
  listTransformations,
  resetTransformations,
  undoTransformation,
  type Operation,
  type Transformation,
} from "../lib/transformations";

const OPERATIONS: { value: Operation; label: string }[] = [
  { value: "drop_duplicates", label: "Drop duplicate rows" },
  { value: "drop_missing_rows", label: "Drop rows with missing values" },
  { value: "drop_columns", label: "Drop columns" },
  { value: "rename_columns", label: "Rename a column" },
  { value: "impute_missing", label: "Fill missing values" },
  { value: "cast_type", label: "Change column type" },
  { value: "handle_outliers", label: "Handle outliers" },
];

const CAST_TYPES = ["integer", "float", "string", "boolean", "datetime", "category"];

export default function CleaningPanel({
  datasetId,
  columns,
  onChanged,
}: {
  datasetId: string;
  columns: ColumnInfo[];
  onChanged: (d: Dataset) => void;
}) {
  const [history, setHistory] = useState<Transformation[]>([]);
  const [op, setOp] = useState<Operation>("drop_duplicates");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Operation-specific fields.
  const colNames = useMemo(() => columns.map((c) => c.name), [columns]);
  const [how, setHow] = useState<"any" | "all">("any");
  const [selectedCols, setSelectedCols] = useState<string[]>([]);
  const [column, setColumn] = useState<string>(colNames[0] ?? "");
  const [newName, setNewName] = useState("");
  const [strategy, setStrategy] = useState("mean");
  const [constValue, setConstValue] = useState("");
  const [castTo, setCastTo] = useState("integer");
  const [method, setMethod] = useState<"clip" | "remove">("clip");

  async function refreshHistory() {
    setHistory(await listTransformations(datasetId));
  }

  useEffect(() => {
    refreshHistory();
  }, [datasetId]);

  // Keep the single-column selector valid as columns change.
  useEffect(() => {
    if (!colNames.includes(column)) setColumn(colNames[0] ?? "");
  }, [colNames, column]);

  function buildParams(): Record<string, unknown> {
    switch (op) {
      case "drop_missing_rows":
        return { how };
      case "drop_columns":
        return { columns: selectedCols };
      case "rename_columns":
        return { mapping: { [column]: newName } };
      case "impute_missing":
        return strategy === "constant"
          ? { column, strategy, value: constValue }
          : { column, strategy };
      case "cast_type":
        return { column, to: castTo };
      case "handle_outliers":
        return { column, method };
      default:
        return {};
    }
  }

  async function onApply() {
    setError(null);
    setBusy(true);
    try {
      const updated = await applyTransformation(datasetId, op, buildParams());
      onChanged(updated);
      await refreshHistory();
      setSelectedCols([]);
      setNewName("");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Could not apply this step.");
    } finally {
      setBusy(false);
    }
  }

  async function onUndo() {
    onChanged(await undoTransformation(datasetId));
    await refreshHistory();
  }

  async function onReset() {
    onChanged(await resetTransformations(datasetId));
    await refreshHistory();
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {/* Add step */}
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="text-sm font-semibold text-slate-700">Add a cleaning step</h3>

        <label className="mt-4 block">
          <span className="text-sm font-medium text-slate-600">Operation</span>
          <select
            value={op}
            onChange={(e) => setOp(e.target.value as Operation)}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            {OPERATIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>

        <div className="mt-4 space-y-3">
          {op === "drop_missing_rows" && (
            <Select
              label="Drop a row if"
              value={how}
              onChange={(v) => setHow(v as "any" | "all")}
              options={[
                { value: "any", label: "any value is missing" },
                { value: "all", label: "all values are missing" },
              ]}
            />
          )}

          {op === "drop_columns" && (
            <div>
              <span className="text-sm font-medium text-slate-600">Columns</span>
              <div className="mt-1 max-h-40 space-y-1 overflow-y-auto rounded-lg border border-slate-200 p-2">
                {colNames.map((name) => (
                  <label key={name} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={selectedCols.includes(name)}
                      onChange={(e) =>
                        setSelectedCols((s) =>
                          e.target.checked
                            ? [...s, name]
                            : s.filter((c) => c !== name),
                        )
                      }
                    />
                    {name}
                  </label>
                ))}
              </div>
            </div>
          )}

          {(op === "rename_columns" ||
            op === "impute_missing" ||
            op === "cast_type" ||
            op === "handle_outliers") && (
            <Select
              label="Column"
              value={column}
              onChange={setColumn}
              options={colNames.map((n) => ({ value: n, label: n }))}
            />
          )}

          {op === "rename_columns" && (
            <label className="block">
              <span className="text-sm font-medium text-slate-600">New name</span>
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
          )}

          {op === "impute_missing" && (
            <>
              <Select
                label="Strategy"
                value={strategy}
                onChange={setStrategy}
                options={["mean", "median", "mode", "constant"].map((s) => ({
                  value: s,
                  label: s,
                }))}
              />
              {strategy === "constant" && (
                <label className="block">
                  <span className="text-sm font-medium text-slate-600">Value</span>
                  <input
                    value={constValue}
                    onChange={(e) => setConstValue(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  />
                </label>
              )}
            </>
          )}

          {op === "cast_type" && (
            <Select
              label="Convert to"
              value={castTo}
              onChange={setCastTo}
              options={CAST_TYPES.map((t) => ({ value: t, label: t }))}
            />
          )}

          {op === "handle_outliers" && (
            <Select
              label="Method (IQR 1.5×)"
              value={method}
              onChange={(v) => setMethod(v as "clip" | "remove")}
              options={[
                { value: "clip", label: "clip to bounds" },
                { value: "remove", label: "remove outlier rows" },
              ]}
            />
          )}
        </div>

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        <button
          onClick={onApply}
          disabled={busy}
          className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-60"
        >
          {busy ? "Applying…" : "Apply step"}
        </button>
      </div>

      {/* History */}
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-700">
            Transformation history
          </h3>
          <div className="flex gap-3 text-sm">
            <button
              onClick={onUndo}
              disabled={history.length === 0}
              className="text-slate-500 hover:text-slate-800 disabled:opacity-40"
            >
              Undo
            </button>
            <button
              onClick={onReset}
              disabled={history.length === 0}
              className="text-slate-400 hover:text-red-600 disabled:opacity-40"
            >
              Reset
            </button>
          </div>
        </div>

        {history.length === 0 ? (
          <p className="mt-4 text-sm text-slate-400">
            No steps applied. The dataset is in its original state.
          </p>
        ) : (
          <ol className="mt-4 space-y-2">
            {history.map((t, i) => (
              <li
                key={t.id}
                className="flex items-start gap-3 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-sm"
              >
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-medium text-indigo-700">
                  {i + 1}
                </span>
                <div>
                  <div className="font-medium text-slate-700">{t.operation}</div>
                  {Object.keys(t.params).length > 0 && (
                    <div className="text-xs text-slate-500">
                      {JSON.stringify(t.params)}
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-slate-600">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
