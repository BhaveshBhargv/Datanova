import { useEffect, useRef, useState, type DragEvent } from "react";
import { Link } from "react-router-dom";
import {
  deleteDataset,
  listDatasets,
  uploadDataset,
  type Dataset,
} from "../lib/datasets";
import { formatBytes, formatDate } from "../lib/format";

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function refresh() {
    setDatasets(await listDatasets());
    setLoading(false);
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setError(null);
    setUploading(true);
    try {
      await uploadDataset(files[0]);
      await refresh();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Upload failed.");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  }

  async function onDelete(id: string) {
    if (!confirm("Delete this dataset? This cannot be undone.")) return;
    await deleteDataset(id);
    await refresh();
  }

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="text-2xl font-semibold text-slate-900">Datasets</h1>
      <p className="mt-1 text-sm text-slate-500">
        Upload a CSV or Excel file, or import from a database connection.
      </p>

      {/* Upload dropzone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`mt-6 cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition ${
          dragging
            ? "border-indigo-400 bg-indigo-50"
            : "border-slate-300 bg-white hover:border-indigo-300"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <p className="font-medium text-slate-700">
          {uploading ? "Uploading…" : "Drop a file here, or click to browse"}
        </p>
        <p className="mt-1 text-xs text-slate-400">CSV or XLSX, up to 50 MB</p>
      </div>
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      {/* Dataset list */}
      <div className="mt-8 overflow-hidden rounded-xl border border-slate-200 bg-white">
        {loading ? (
          <div className="p-6 text-sm text-slate-500">Loading…</div>
        ) : datasets.length === 0 ? (
          <div className="p-6 text-sm text-slate-500">No datasets yet.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Source</th>
                <th className="px-4 py-3 font-medium">Rows</th>
                <th className="px-4 py-3 font-medium">Cols</th>
                <th className="px-4 py-3 font-medium">Size</th>
                <th className="px-4 py-3 font-medium">Created</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {datasets.map((d) => (
                <tr key={d.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link
                      to={`/datasets/${d.id}`}
                      className="font-medium text-indigo-600 hover:underline"
                    >
                      {d.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {d.source_type === "upload"
                      ? d.file_format?.toUpperCase()
                      : "Database"}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {d.n_rows.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{d.n_columns}</td>
                  <td className="px-4 py-3 text-slate-600">
                    {formatBytes(d.size_bytes)}
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {formatDate(d.created_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => onDelete(d.id)}
                      className="text-sm text-slate-400 hover:text-red-600"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
