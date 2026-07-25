import { api } from "./api";

export type ChartType =
  | "histogram"
  | "bar"
  | "pie"
  | "box"
  | "scatter"
  | "correlation_heatmap"
  | "line";

export interface ChartSpec {
  type: ChartType;
  column?: string;
  x?: string;
  y?: string;
  bins?: number;
  top_n?: number;
}

export interface ChartData {
  type: ChartType;
  title: string;
  x_label: string | null;
  y_label: string | null;
  categories: unknown[] | null;
  series: { name: string; data: unknown }[];
  extra: Record<string, unknown>;
}

export interface RecommendedChart {
  type: ChartType;
  reason: string;
  column?: string | null;
  x?: string | null;
  y?: string | null;
}

export interface EdaSummary {
  numeric: Record<string, Record<string, number | null>>;
  correlations: { columns: string[]; matrix: (number | null)[][] };
  recommended_charts: RecommendedChart[];
}

export interface ExplainResponse {
  text: string;
  source: "llm" | "fallback";
}

export async function getEdaSummary(id: string): Promise<EdaSummary> {
  const { data } = await api.get<EdaSummary>(`/datasets/${id}/eda/summary`);
  return data;
}

export async function postChart(id: string, spec: ChartSpec): Promise<ChartData> {
  const { data } = await api.post<ChartData>(`/datasets/${id}/chart`, spec);
  return data;
}

export async function explain(
  id: string,
  kind: "overview" | "chart",
  spec?: ChartSpec,
): Promise<ExplainResponse> {
  const { data } = await api.post<ExplainResponse>(`/datasets/${id}/explain`, {
    kind,
    spec: spec ?? null,
  });
  return data;
}
