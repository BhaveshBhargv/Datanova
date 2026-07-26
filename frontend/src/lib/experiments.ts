import { api } from "./api";

export interface ModelResult {
  model: string;
  metrics: Record<string, number | null | string>;
}

export interface Experiment {
  id: string;
  dataset_id: string;
  target_column: string;
  feature_columns: string[];
  problem_type: "classification" | "regression";
  status: "running" | "completed" | "failed";
  test_size: number;
  results: ModelResult[] | null;
  best_model_name: string | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}

export async function listExperiments(datasetId: string): Promise<Experiment[]> {
  const { data } = await api.get<Experiment[]>(
    `/datasets/${datasetId}/experiments`,
  );
  return data;
}

export async function createExperiment(
  datasetId: string,
  payload: { target: string; features?: string[]; test_size?: number },
): Promise<Experiment> {
  const { data } = await api.post<Experiment>(
    `/datasets/${datasetId}/experiments`,
    payload,
  );
  return data;
}

export async function getExperiment(id: string): Promise<Experiment> {
  const { data } = await api.get<Experiment>(`/experiments/${id}`);
  return data;
}

export async function deleteExperiment(id: string): Promise<void> {
  await api.delete(`/experiments/${id}`);
}
