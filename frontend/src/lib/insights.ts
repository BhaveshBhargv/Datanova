import { api } from "./api";
import type { ExplainResponse } from "./eda";

export type Severity = "critical" | "warning" | "info";

export interface Insight {
  category: string;
  severity: Severity;
  title: string;
  detail: string;
  recommendation: string | null;
}

export interface InsightsResponse {
  total: number;
  counts: Record<string, number>;
  insights: Insight[];
}

export async function getInsights(datasetId: string): Promise<InsightsResponse> {
  const { data } = await api.get<InsightsResponse>(
    `/datasets/${datasetId}/insights`,
  );
  return data;
}

export async function getInsightsNarrative(
  datasetId: string,
): Promise<ExplainResponse> {
  const { data } = await api.post<ExplainResponse>(
    `/datasets/${datasetId}/insights/narrative`,
  );
  return data;
}
