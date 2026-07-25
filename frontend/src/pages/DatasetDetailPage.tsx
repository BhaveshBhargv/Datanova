import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  getDataset,
  previewDataset,
  renameDataset,
  type Dataset,
  type DatasetPreview,
} from "../lib/datasets";
import { cellText, formatDate } from "../lib/format";

export default function DatasetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");

  useEffect(() => {
    if (!id) return;
    (async () => {
      try {
        const ds = await getDataset(id);
        setDataset(ds);
        setName(ds.name);
        setPreview(await previewDataset(id, 50));
      } catch {
        setError("Could not load this dataset.");
      }
    })();
  }, [id]);

  async function saveName() {
    if (!id) return;
    const updated = await renameDataset(id, name);
    setDataset(updated);
    setEditing(false);
  }

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!dataset) return <p className="text-sm text-slate-500">Loading…</p>;

  return (
    <div className="mx-auto max-w-5xl">
      <Link to="/datasets" className="text-sm text-indigo-600 hover:underline">
        ← Datasets
      </Link>

      <div className="mt-3 flex items-center gap-3">
        {editing ? (
          <>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-lg"
            />
            <button
              onClick={saveName}
              className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500"
            >
              Save
            </button>
            <button
              onClick={() => {
                setEditing(false);
                setName(dataset.name);
              }}
              className="text-sm text-slate-500"
            >
              Cancel
            </button>
          </>
        ) : (
          <>
            <h1 className="text-2xl font-semibold text-slate-900">
              {dataset.name}
            </h1>
            <button
              onClick={() => setEditing(true)}
              className="text-sm text-slate-400 hover:text-indigo-600"
            >
              Rename
            </button>
          </>
        )}
      </div>

      <div className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-sm text-slate-500">
        <span>{dataset.n_rows.toLocaleString()} rows</span>
        <span>{dataset.n_columns} columns</span>
        <span>
          {dataset.source_type === "upload"
            ? `${dataset.file_format?.toUpperCase()} upload`
            : "Database import"}
        </span>
        <span>Created {formatDate(dataset.created_at)}</span>
      </div>

      {/* Schema */}
      <h2 className="mt-8 text-sm font-semibold uppercase tracking-wide text-slate-500">
        Schema
      </h2>
      <div className="mt-2 flex flex-wrap gap-2">
        {dataset.columns.map((c) => (
          <span
            key={c.name}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm"
          >
            <span className="font-medium text-slate-700">{c.name}</span>
            <span className="text-xs text-slate-400">{c.dtype}</span>
            {c.nullable && (
              <span className="text-xs text-amber-500">nullable</span>
            )}
          </span>
        ))}
      </div>

      {/* Preview */}
      <h2 className="mt-8 text-sm font-semibold uppercase tracking-wide text-slate-500">
        Preview
      </h2>
      <div className="mt-2 overflow-x-auto rounded-xl border border-slate-200 bg-white">
        {preview && (
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                {preview.columns.map((c) => (
                  <th key={c} className="whitespace-nowrap px-4 py-2 font-medium">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {preview.rows.map((row, i) => (
                <tr key={i} className="hover:bg-slate-50">
                  {preview.columns.map((c) => (
                    <td key={c} className="whitespace-nowrap px-4 py-2 text-slate-700">
                      {cellText(row[c])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <button
        onClick={() => navigate("/datasets")}
        className="mt-6 text-sm text-slate-500 hover:text-slate-700"
      >
        Done
      </button>
    </div>
  );
}
