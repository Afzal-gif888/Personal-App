import { useState, useCallback, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { chatService, CHAT_UI_STORAGE_KEYS } from '../services/chatService';
import type { Conversation, ChatMessage } from '../types';
import { toast } from '../stores/notificationStore';
import { errorMessage } from '../services/api';
import { invalidateAfterApproval } from './useApprovals';

export function useChat() {
  const queryClient = useQueryClient();

  // Temporary UI state: Active conversation ID in localStorage
  const [selectedConversationId, setActiveIdState] = useState<string>(() => {
    try {
      return localStorage.getItem(CHAT_UI_STORAGE_KEYS.ACTIVE_CONVERSATION_ID) || '';
    } catch {
      return '';
    }
  });

  // Query: Conversations list
  const conversationsQuery = useQuery({
    queryKey: ['conversations'],
    queryFn: () => chatService.getConversations(),
  });

  const conversations = useMemo(() => conversationsQuery.data ?? [], [conversationsQuery.data]);

  // Fall back to the most recent conversation when the stored selection no longer exists
  const activeConversationId = conversations.some((c) => c.id === selectedConversationId)
    ? selectedConversationId
    : conversations[0]?.id ?? '';

  const selectConversation = useCallback((id: string) => {
    setActiveIdState(id);
    try {
      localStorage.setItem(CHAT_UI_STORAGE_KEYS.ACTIVE_CONVERSATION_ID, id);
    } catch {
      // ignore
    }
  }, []);

  // Query: Messages for current active conversation
  const messagesQuery = useQuery({
    queryKey: ['chatMessages', activeConversationId],
    queryFn: () => chatService.getMessages(activeConversationId),
    enabled: Boolean(activeConversationId),
  });

  // Mutation: Create new conversation
  const createConversationMutation = useMutation({
    mutationFn: (title?: string) => chatService.createConversation(title),
    onSuccess: (newConv: Conversation) => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      selectConversation(newConv.id);
      queryClient.setQueryData(['chatMessages', newConv.id], () => []);
    },
    onError: () => toast.error('Failed to start a new chat'),
  });

  // Mutation: Send message in active conversation
  const sendMutation = useMutation({
    mutationFn: async (text: string) => {
      let targetConvId = activeConversationId;
      if (!targetConvId) {
        const newConv = await chatService.createConversation();
        targetConvId = newConv.id;
        selectConversation(targetConvId);
        queryClient.invalidateQueries({ queryKey: ['conversations'] });
      }
      const result = await chatService.sendMessage(targetConvId, text);
      return { conversationId: targetConvId, ...result };
    },
    onSuccess: ({ conversationId }) => {
      // Use the id the message was actually sent to — it may be a conversation created above
      queryClient.invalidateQueries({ queryKey: ['chatMessages', conversationId] });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      queryClient.invalidateQueries({ queryKey: ['agentRuns'] });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    },
    onError: (err) => toast.error('Failed to send message', errorMessage(err)),
  });

  // Mutation: Retry message
  const retryMutation = useMutation({
    mutationFn: (messageId: string) => chatService.retryMessage(activeConversationId, messageId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chatMessages', activeConversationId] });
      toast.info('Message resent');
    },
    onError: () => toast.error('Failed to retry message'),
  });

  // Mutation: Rename conversation
  const renameMutation = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      chatService.renameConversation(id, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      toast.success('Conversation renamed');
    },
    onError: () => toast.error('Failed to rename conversation'),
  });

  // Mutation: Delete conversation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => chatService.deleteConversation(id),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      if (activeConversationId === deletedId) {
        const remaining = conversations.filter((c) => c.id !== deletedId);
        const nextId = remaining[0]?.id || '';
        selectConversation(nextId);
      }
      toast.info('Conversation deleted');
    },
    onError: () => toast.error('Failed to delete conversation'),
  });

  // Mutation: Approve or reject one proposed action
  const actionDecisionMutation = useMutation({
    mutationFn: ({ approvalId, decision }: { approvalId: string; decision: 'approved' | 'rejected' }) =>
      chatService.decideAction(approvalId, decision),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['chatMessages', activeConversationId] });
      invalidateAfterApproval(queryClient);
      toast.success(
        variables.decision === 'approved' ? 'Action Approved' : 'Action Rejected',
        variables.decision === 'approved' ? 'Saved to your workspace.' : 'No changes were made.'
      );
    },
    onError: (err) => {
      // e.g. the approval expired: refresh so the card shows its real status
      queryClient.invalidateQueries({ queryKey: ['chatMessages', activeConversationId] });
      toast.error('Could not complete the action', errorMessage(err));
    },
  });

  // Mutation: Clear active conversation history
  const clearMutation = useMutation({
    mutationFn: () => chatService.clearHistory(activeConversationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chatMessages', activeConversationId] });
      toast.info('Chat history cleared');
    },
  });

  const activeConversation = conversations.find((c) => c.id === activeConversationId);

  return {
    conversations,
    isLoadingConversations: conversationsQuery.isLoading,
    activeConversation,
    activeConversationId,
    selectConversation,
    createConversation: createConversationMutation.mutateAsync,
    isCreatingConversation: createConversationMutation.isPending,
    messages: (messagesQuery.data || []) as ChatMessage[],
    isLoadingMessages: messagesQuery.isLoading,
    isErrorMessages: messagesQuery.isError,
    sendMessage: sendMutation.mutateAsync,
    isSending: sendMutation.isPending,
    retryMessage: retryMutation.mutateAsync,
    isRetrying: retryMutation.isPending,
    renameConversation: renameMutation.mutateAsync,
    isRenaming: renameMutation.isPending,
    deleteConversation: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,
    handleActionDecision: actionDecisionMutation.mutateAsync,
    isDeciding: actionDecisionMutation.isPending,
    clearHistory: clearMutation.mutateAsync,
  };
}
