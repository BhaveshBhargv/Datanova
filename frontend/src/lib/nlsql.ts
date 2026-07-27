import { api } from "./api";

export interface SchemaColumn {
  name: string;
  type: string;
}

export interface SchemaTable {
  table: string;
  columns: SchemaColumn[];
}

export interface NLQueryResponse {
  sql: string | null;
  columns: string[] | null;
  rows: Record<string, unknown>[] | null;
  row_count: number | null;
  plan: string[];
  optimization_notes: string[];
  explanation: string;
  source: "llm" | "fallback" | null;
  error: string | null;
}

export interface QueryHistoryItem {
  id: string;
  question: string;
  sql: string | null;
  explanation: string | null;
  source: string | null;
  row_count: number | null;
  error: string | null;
  created_at: string;
}

export async function getSchema(connectionId: string): Promise<SchemaTable[]> {
  const { data } = await api.get<{ tables: SchemaTable[] }>(
    `/connections/${connectionId}/schema`,
  );
  return data.tables;
}

export async function queryConnection(
  connectionId: string,
  question: string,
): Promise<NLQueryResponse> {
  const { data } = await api.post<NLQueryResponse>(
    `/connections/${connectionId}/query`,
    { question },
  );
  return data;
}

export async function listQueries(
  connectionId: string,
): Promise<QueryHistoryItem[]> {
  const { data } = await api.get<QueryHistoryItem[]>(
    `/connections/${connectionId}/queries`,
  );
  return data;
}

export async function deleteQuery(
  connectionId: string,
  queryId: string,
): Promise<void> {
  await api.delete(`/connections/${connectionId}/queries/${queryId}`);
}
