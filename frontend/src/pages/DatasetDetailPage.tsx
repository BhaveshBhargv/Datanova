import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  getDataset,
  previewDataset,
  renameDataset,
  type Dataset,
  type DatasetPreview,
} from "../lib/datasets";
import { cellText, formatDate } from "../lib/format";
import ProfilePanel from "../components/ProfilePanel";
import CleaningPanel from "../components/CleaningPanel";
import ExplorePanel from "../components/ExplorePanel";
import AssistantPanel from "../components/AssistantPanel";
import ModelsPanel from "../components/ModelsPanel";
import InsightsPanel from "../components/InsightsPanel";

type Tab =
  | "preview"
  | "profile"
  | "explore"
  | "insights"
  | "assistant"
  | "models"
  | "cleaning";

export default function DatasetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("preview");
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  // Bumped whenever the underlying data changes, to refresh preview/profile.
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (!id) return;
    getDataset(id)
      .then((ds) => {
        setDataset(ds);
        setName(ds.name);
      })
      .catch(() => setError("Could not load this dataset."));
  }, [id]);

  const onDataChanged = useCallback((updated: Dataset) => {
    setDataset(updated);
    setVersion((v) => v + 1);
  }, []);

  async function saveName() {
    if (!id) return;
    const updated = await renameDataset(id, name);
    setDataset(updated);
    setEditing(false);
  }

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!dataset || !id) return <p className="text-sm text-slate-500">Loading…</p>;

  const tabs: { key: Tab; label: string }[] = [
    { key: "preview", label: "Preview" },
    { key: "profile", label: "Profile" },
    { key: "explore", label: "Explore" },
    { key: "insights", label: "Insights" },
    { key: "assistant", label: "Assistant" },
    { key: "models", label: "Models" },
    { key: "cleaning", label: "Cleaning" },
  ];

  return (
    <div className="mx-auto max-w-6xl">
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
            <h1 className="text-2xl font-semibold text-slate-900">{dataset.name}</h1>
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

      {/* Tabs */}
      <div className="mt-6 flex gap-1 border-b border-slate-200">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition ${
              tab === t.key
                ? "border-indigo-600 text-indigo-700"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {tab === "preview" && <PreviewTab datasetId={id} version={version} />}
        {tab === "profile" && <ProfilePanel datasetId={id} version={version} />}
        {tab === "explore" && (
          <ExplorePanel
            datasetId={id}
            columns={dataset.columns}
            version={version}
          />
        )}
        {tab === "insights" && (
          <InsightsPanel datasetId={id} version={version} />
        )}
        {tab === "assistant" && (
          <AssistantPanel datasetId={id} columns={dataset.columns} />
        )}
        {tab === "models" && (
          <ModelsPanel
            datasetId={id}
            columns={dataset.columns}
            rowCount={dataset.n_rows}
          />
        )}
        {tab === "cleaning" && (
          <CleaningPanel
            datasetId={id}
            columns={dataset.columns}
            onChanged={onDataChanged}
          />
        )}
      </div>
    </div>
  );
}

function PreviewTab({
  datasetId,
  version,
}: {
  datasetId: string;
  version: number;
}) {
  const [preview, setPreview] = useState<DatasetPreview | null>(null);

  useEffect(() => {
    previewDataset(datasetId, 50).then(setPreview);
  }, [datasetId, version]);

  if (!preview) return <p className="text-sm text-slate-500">Loading…</p>;

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
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
    </div>
  );
}
