import { api } from "./api";

export interface TopValue {
  value: unknown;
  count: number;
}

export interface ColumnProfile {
  name: string;
  dtype: string;
  count: number;
  missing: number;
  missing_pct: number;
  unique: number;
  suggested_type: string | null;
  min?: unknown;
  max?: unknown;
  mean?: number | null;
  median?: number | null;
  std?: number | null;
  q1?: number | null;
  q3?: number | null;
  outliers?: number | null;
  top_values?: TopValue[] | null;
}

export interface DatasetProfile {
  n_rows: number;
  n_columns: number;
  duplicate_rows: number;
  missing_cells: number;
  missing_pct: number;
  memory_bytes: number;
  quality_score: number;
  columns: ColumnProfile[];
}

export async function getProfile(id: string): Promise<DatasetProfile> {
  const { data } = await api.get<DatasetProfile>(`/datasets/${id}/profile`);
  return data;
}
