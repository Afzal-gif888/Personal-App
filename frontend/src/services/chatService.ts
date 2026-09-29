import type { ActionCardData, AgentStep, ChatMessage, Conversation } from '../types';
import { api } from './api';

// UI-only state kept in the browser; conversations and messages live on the server.
export const CHAT_UI_STORAGE_KEYS = {
  ACTIVE_CONVERSATION_ID: 'agentos_active_conversation_id',
  DRAFT_MESSAGE_PREFIX: 'agentos_chat_draft_',
  SIDEBAR_COLLAPSED: 'agentos_chat_sidebar_collapsed',
};

interface ActionOut {
  approvalId: string;
  action: string;
  actionLabel: string;
  title: string;
  description: string | null;
  details: Record<string, unknown>;
  status: ActionCardData['status'];
}

interface MessageOut {
  id: string;
  conversationId: string;
  role: ChatMessage['role'] | 'tool';
  content: string;
  metadata: {
    status?: 'success' | 'error';
    error?: string;
    steps?: AgentStep[];
    actions?: ActionOut[];
  };
  agentRunId: string | null;
  createdAt: string;
}

interface SendMessageOut {
  userMessage: MessageOut;
  assistantMessage: MessageOut;
  conversation: Conversation;
}

function toMessage(m: MessageOut): ChatMessage {
  const { actions, ...meta } = m.metadata ?? {};
  return {
    id: m.id,
    conversationId: m.conversationId,
    role: m.role === 'tool' ? 'system' : m.role,
    content: m.content,
    createdAt: m.createdAt,
    agentRunId: m.agentRunId,
    metadata: {
      ...meta,
      actions: (actions ?? []).map((a) => ({
        approvalId: a.approvalId,
        type: a.action,
        label: a.actionLabel,
        title: a.title,
        description: a.description ?? undefined,
        details: a.details,
        status: a.status,
      })),
    },
  };
}

export const chatService = {
  async getConversations(): Promise<Conversation[]> {
    return api.get<Conversation[]>('/conversations');
  },

  async getConversation(id: string): Promise<Conversation> {
    return api.get<Conversation>(`/conversations/${id}`);
  },

  async createConversation(title?: string): Promise<Conversation> {
    return api.post<Conversation>('/conversations', title ? { title } : {});
  },

  async getMessages(conversationId: string): Promise<ChatMessage[]> {
    const messages = await api.get<MessageOut[]>(`/conversations/${conversationId}/messages`);
    return messages.filter((m) => m.role !== 'tool').map(toMessage);
  },

  /** Runs the agent. Proposed changes come back as pending approvals on the assistant message. */
  async sendMessage(
    conversationId: string,
    text: string
  ): Promise<{ userMessage: ChatMessage; assistantMessage: ChatMessage; conversation: Conversation }> {
    const res = await api.post<SendMessageOut>(`/conversations/${conversationId}/messages`, { content: text });
    return {
      userMessage: toMessage(res.userMessage),
      assistantMessage: toMessage(res.assistantMessage),
      conversation: res.conversation,
    };
  },

  async renameConversation(id: string, title: string): Promise<Conversation> {
    return api.patch<Conversation>(`/conversations/${id}`, { title: title.trim() || 'Untitled conversation' });
  },

  async deleteConversation(id: string): Promise<void> {
    await api.delete(`/conversations/${id}`);
  },

  /** Re-sends the user message that preceded a failed assistant reply. */
  async retryMessage(conversationId: string, messageId: string): Promise<ChatMessage> {
    const messages = await chatService.getMessages(conversationId);
    const index = messages.findIndex((m) => m.id === messageId);
    const prompt = [...messages.slice(0, index + 1)].reverse().find((m) => m.role === 'user');
    if (!prompt) throw new Error('Nothing to retry');
    return (await chatService.sendMessage(conversationId, prompt.content)).assistantMessage;
  },

  /** Approve or reject one proposed action (an approval) from a chat card. */
  async decideAction(approvalId: string, decision: 'approved' | 'rejected'): Promise<void> {
    await api.post(`/approvals/${approvalId}/${decision === 'approved' ? 'approve' : 'reject'}`);
  },

  async clearHistory(conversationId: string): Promise<void> {
    await api.delete(`/conversations/${conversationId}/messages`);
  },
};
