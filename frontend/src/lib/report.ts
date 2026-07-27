import { api } from "./api";

export interface ReportData {
  dataset: {
    name: string;
    n_rows: number;
    n_columns: number;
    source_type: string;
    created_at: string | null;
  };
  profile: { quality_score: number; missing_pct: number; duplicate_rows: number };
  eda: { correlations: { columns: string[] } };
  experiment: { target: string; problem_type: string; best_model_name: string } | null;
  importance: { feature: string; importance: number }[] | null;
  insights_counts: Record<string, number>;
  summary: {
    overview: string;
    overview_source: "llm" | "fallback";
    insights: string;
    insights_source: "llm" | "fallback";
  };
}

export async function getReport(datasetId: string): Promise<ReportData> {
  const { data } = await api.get<ReportData>(`/datasets/${datasetId}/report`);
  return data;
}

export async function downloadReport(
  datasetId: string,
  format: "pdf" | "excel",
  datasetName: string,
): Promise<void> {
  const res = await api.get(`/datasets/${datasetId}/report/${format}`, {
    responseType: "blob",
  });
  const ext = format === "excel" ? "xlsx" : "pdf";
  const safe = datasetName.replace(/[^a-zA-Z0-9-_]/g, "_") || "report";
  const url = URL.createObjectURL(res.data as Blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${safe}_report.${ext}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
