import { api } from "./api";
import type { Dataset } from "./datasets";

export type Dialect = "postgresql" | "mysql" | "sqlite";

export interface Connection {
  id: string;
  name: string;
  dialect: Dialect;
  host: string | null;
  port: number | null;
  database: string;
  username: string | null;
  created_at: string;
}

export interface ConnectionCreate {
  name: string;
  dialect: Dialect;
  database: string;
  host?: string | null;
  port?: number | null;
  username?: string | null;
  password?: string | null;
}

export interface TestResult {
  ok: boolean;
  message: string;
}

export async function listConnections(): Promise<Connection[]> {
  const { data } = await api.get<Connection[]>("/connections");
  return data;
}

export async function createConnection(
  payload: ConnectionCreate,
): Promise<Connection> {
  const { data } = await api.post<Connection>("/connections", payload);
  return data;
}

export async function testConnection(id: string): Promise<TestResult> {
  const { data } = await api.post<TestResult>(`/connections/${id}/test`);
  return data;
}

export async function listTables(id: string): Promise<string[]> {
  const { data } = await api.get<{ tables: string[] }>(
    `/connections/${id}/tables`,
  );
  return data.tables;
}

export async function importFrom(
  id: string,
  payload: { table?: string; query?: string; name?: string },
): Promise<Dataset> {
  const { data } = await api.post<Dataset>(`/connections/${id}/import`, payload);
  return data;
}

export async function deleteConnection(id: string): Promise<void> {
  await api.delete(`/connections/${id}`);
}
