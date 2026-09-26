import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { chatService, CHAT_UI_STORAGE_KEYS } from '../services/chatService';
import type { Conversation, ChatMessage } from '../types';
import { toast } from '../stores/notificationStore';

export function useChat() {
  const queryClient = useQueryClient();

  // Temporary UI state: Active conversation ID in localStorage
  const [activeConversationId, setActiveIdState] = useState<string>(() => {
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

  const conversations = conversationsQuery.data || [];

  // Automatically select the first conversation if none is selected or selected one doesn't exist
  useEffect(() => {
    if (conversations.length > 0) {
      const exists = conversations.some((c) => c.id === activeConversationId);
      if (!activeConversationId || !exists) {
        const defaultId = conversations[0].id;
        setActiveIdState(defaultId);
        try {
          localStorage.setItem(CHAT_UI_STORAGE_KEYS.ACTIVE_CONVERSATION_ID, defaultId);
        } catch {
          // ignore
        }
      }
    }
  }, [conversations, activeConversationId]);

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
      return chatService.sendMessage(targetConvId, text);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chatMessages', activeConversationId] });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      queryClient.invalidateQueries({ queryKey: ['agentRuns'] });
    },
    onError: () => toast.error('Failed to send message'),
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

  // Mutation: Handle action decision (approve/reject)
  const actionDecisionMutation = useMutation({
    mutationFn: ({ messageId, decision }: { messageId: string; decision: 'approved' | 'rejected' }) =>
      chatService.handleActionCardDecision(messageId, decision),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['chatMessages', activeConversationId] });
      queryClient.invalidateQueries({ queryKey: ['reminders'] });
      queryClient.invalidateQueries({ queryKey: ['studySessions'] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      toast.success(
        variables.decision === 'approved' ? 'Action Approved' : 'Action Rejected',
        variables.decision === 'approved' ? 'Resource created in your workspace.' : 'Action cancelled.'
      );
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
