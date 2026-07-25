import { api } from "./api";
import type { Dataset } from "./datasets";

export type Operation =
  | "drop_duplicates"
  | "drop_missing_rows"
  | "drop_columns"
  | "rename_columns"
  | "impute_missing"
  | "cast_type"
  | "handle_outliers";

export interface Transformation {
  id: string;
  order_index: number;
  operation: Operation;
  params: Record<string, unknown>;
  created_at: string;
}

export async function listTransformations(
  id: string,
): Promise<Transformation[]> {
  const { data } = await api.get<Transformation[]>(
    `/datasets/${id}/transformations`,
  );
  return data;
}

export async function applyTransformation(
  id: string,
  operation: Operation,
  params: Record<string, unknown>,
): Promise<Dataset> {
  const { data } = await api.post<Dataset>(`/datasets/${id}/transformations`, {
    operation,
    params,
  });
  return data;
}

export async function undoTransformation(id: string): Promise<Dataset> {
  const { data } = await api.post<Dataset>(
    `/datasets/${id}/transformations/undo`,
  );
  return data;
}

export async function resetTransformations(id: string): Promise<Dataset> {
  const { data } = await api.post<Dataset>(
    `/datasets/${id}/transformations/reset`,
  );
  return data;
}
