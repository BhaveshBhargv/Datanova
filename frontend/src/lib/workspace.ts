import { api } from "./api";

export interface WorkspaceSummary {
  counts: { datasets: number; connections: number; models: number; chats: number };
  recent_datasets: {
    id: string;
    name: string;
    n_rows: number;
    n_columns: number;
    source_type: string;
    created_at: string;
  }[];
  recent_models: {
    id: string;
    dataset_id: string;
    dataset_name: string;
    target: string;
    problem_type: string;
    best_model_name: string | null;
    created_at: string | null;
  }[];
  recent_queries: {
    id: string;
    connection_id: string;
    connection_name: string;
    question: string;
    created_at: string;
  }[];
}

export async function getWorkspaceSummary(): Promise<WorkspaceSummary> {
  const { data } = await api.get<WorkspaceSummary>("/workspace/summary");
  return data;
}
