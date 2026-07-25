import { api } from "./api";

export interface ColumnInfo {
  name: string;
  dtype: string;
  nullable: boolean;
}

export interface Dataset {
  id: string;
  name: string;
  source_type: "upload" | "database";
  file_format: string | null;
  n_rows: number;
  n_columns: number;
  size_bytes: number | null;
  columns: ColumnInfo[];
  status: string;
  error: string | null;
  created_at: string;
}

export interface DatasetPreview {
  columns: string[];
  rows: Record<string, unknown>[];
}

export async function listDatasets(): Promise<Dataset[]> {
  const { data } = await api.get<Dataset[]>("/datasets");
  return data;
}

export async function getDataset(id: string): Promise<Dataset> {
  const { data } = await api.get<Dataset>(`/datasets/${id}`);
  return data;
}

export async function uploadDataset(file: File): Promise<Dataset> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<Dataset>("/datasets/upload", form);
  return data;
}

export async function previewDataset(
  id: string,
  rows = 50,
): Promise<DatasetPreview> {
  const { data } = await api.get<DatasetPreview>(
    `/datasets/${id}/preview?rows=${rows}`,
  );
  return data;
}

export async function renameDataset(id: string, name: string): Promise<Dataset> {
  const { data } = await api.patch<Dataset>(`/datasets/${id}`, { name });
  return data;
}

export async function deleteDataset(id: string): Promise<void> {
  await api.delete(`/datasets/${id}`);
}
