import { api } from "./api";
import type { ExplainResponse } from "./eda";

export interface FeatureImportance {
  feature: string;
  importance: number;
}

export interface ImportanceResponse {
  problem_type: string;
  target: string;
  sample_size: number;
  importance: FeatureImportance[];
}

export interface Contribution {
  feature: string;
  value: unknown;
  contribution: number;
}

export interface PredictionExplanation {
  index: number;
  prediction: unknown;
  predicted_label: unknown;
  proba: Record<string, number> | null;
  base_value: number;
  contributions: Contribution[];
}

export async function getImportance(
  experimentId: string,
): Promise<ImportanceResponse> {
  const { data } = await api.get<ImportanceResponse>(
    `/experiments/${experimentId}/importance`,
  );
  return data;
}

export async function explainPrediction(
  experimentId: string,
  index: number,
): Promise<PredictionExplanation> {
  const { data } = await api.post<PredictionExplanation>(
    `/experiments/${experimentId}/predictions/explain`,
    { index },
  );
  return data;
}

export async function getDriverNarrative(
  experimentId: string,
): Promise<ExplainResponse> {
  const { data } = await api.post<ExplainResponse>(
    `/experiments/${experimentId}/narrative`,
  );
  return data;
}
