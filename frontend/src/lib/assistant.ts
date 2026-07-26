import { api } from "./api";

export interface AssistantMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sql?: string | null;
  result_columns?: string[] | null;
  result_rows?: Record<string, unknown>[] | null;
  error?: string | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  dataset_id: string;
  title: string;
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: AssistantMessage[];
}

export async function listConversations(
  datasetId: string,
): Promise<Conversation[]> {
  const { data } = await api.get<Conversation[]>(
    `/datasets/${datasetId}/conversations`,
  );
  return data;
}

export async function createConversation(
  datasetId: string,
  title = "Chat",
): Promise<Conversation> {
  const { data } = await api.post<Conversation>(
    `/datasets/${datasetId}/conversations`,
    { title },
  );
  return data;
}

export async function getConversation(
  conversationId: string,
): Promise<ConversationDetail> {
  const { data } = await api.get<ConversationDetail>(
    `/conversations/${conversationId}`,
  );
  return data;
}

export async function postMessage(
  conversationId: string,
  content: string,
): Promise<AssistantMessage> {
  const { data } = await api.post<AssistantMessage>(
    `/conversations/${conversationId}/messages`,
    { content },
  );
  return data;
}

/** Load the dataset's default conversation, creating one if none exists. */
export async function getOrCreateConversation(
  datasetId: string,
): Promise<ConversationDetail> {
  const existing = await listConversations(datasetId);
  const conv = existing[0] ?? (await createConversation(datasetId));
  return getConversation(conv.id);
}
