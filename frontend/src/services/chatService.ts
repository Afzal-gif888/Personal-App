import type { Conversation, ChatMessage, ActionCardData, AgentRun, AgentStep } from '../types';
import { INITIAL_CONVERSATIONS, INITIAL_CONVERSATION_MESSAGES } from '../mocks/conversations';
import { storage } from './storage';
import { reminderService } from './reminderService';
import { studyPlanService } from './studyPlanService';

const delay = (ms = 150) => new Promise((resolve) => setTimeout(resolve, ms));

// Temporary UI State storage keys in localStorage (permitted by specification)
export const CHAT_UI_STORAGE_KEYS = {
  ACTIVE_CONVERSATION_ID: 'agentos_active_conversation_id',
  DRAFT_MESSAGE_PREFIX: 'agentos_chat_draft_',
  SIDEBAR_COLLAPSED: 'agentos_chat_sidebar_collapsed',
};

// In-Memory persistent mock database simulating FastAPI backend + PostgreSQL
// Isolates data per user; does NOT persist in localStorage as per requirement
let mockConversationsDb: Conversation[] = [...INITIAL_CONVERSATIONS];
let mockMessagesDb: Record<string, ChatMessage[]> = { ...INITIAL_CONVERSATION_MESSAGES };

export const chatService = {
  /**
   * Get all conversations belonging to the authenticated user.
   * Matches FastAPI endpoint: GET /api/conversations
   */
  async getConversations(): Promise<Conversation[]> {
    await delay(120);
    const currentUser = storage.getUser();
    const userId = currentUser?.id || 'usr-alex-101';

    // User isolation: Only return conversations belonging to this user
    return mockConversationsDb
      .filter((conv) => !conv.user_id || conv.user_id === userId)
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
  },

  /**
   * Get a single conversation by ID.
   * Matches FastAPI endpoint: GET /api/conversations/{id}
   */
  async getConversation(id: string): Promise<Conversation> {
    await delay(80);
    const conv = mockConversationsDb.find((c) => c.id === id);
    if (!conv) {
      throw new Error(`Conversation not found: ${id}`);
    }
    return { ...conv };
  },

  /**
   * Create a new conversation for the authenticated user.
   * Matches FastAPI endpoint: POST /api/conversations
   */
  async createConversation(title = 'New Conversation'): Promise<Conversation> {
    await delay(100);
    const currentUser = storage.getUser();
    const userId = currentUser?.id || 'usr-alex-101';

    const newConv: Conversation = {
      id: `conv-${Date.now()}`,
      user_id: userId,
      title,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    mockConversationsDb = [newConv, ...mockConversationsDb];
    mockMessagesDb[newConv.id] = [
      {
        id: `msg-welcome-${Date.now()}`,
        conversation_id: newConv.id,
        role: 'assistant',
        sender: 'assistant',
        content: `Hello! I'm AgentOS, your Personal AI Operating System. How can I help you across your academics, calendar, bills, expenses, or goals today?`,
        text: `Hello! I'm AgentOS, your Personal AI Operating System. How can I help you across your academics, calendar, bills, expenses, or goals today?`,
        created_at: new Date().toISOString(),
        timestamp: new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit' }).format(new Date()),
      },
    ];

    // Persist selected conversation in temporary UI storage
    try {
      localStorage.setItem(CHAT_UI_STORAGE_KEYS.ACTIVE_CONVERSATION_ID, newConv.id);
    } catch {
      // ignore
    }

    return newConv;
  },

  /**
   * Retrieve all messages for a specific conversation.
   * Matches FastAPI endpoint: GET /api/conversations/{conversationId}/messages
   */
  async getMessages(conversationId?: string): Promise<ChatMessage[]> {
    await delay(120);
    if (!conversationId) {
      // If no ID is passed, default to first conversation or active stored conversation
      const activeId = localStorage.getItem(CHAT_UI_STORAGE_KEYS.ACTIVE_CONVERSATION_ID) || mockConversationsDb[0]?.id;
      if (!activeId) return [];
      return [...(mockMessagesDb[activeId] || [])];
    }
    return [...(mockMessagesDb[conversationId] || [])];
  },

  /**
   * Send a message to the AI agent within a conversation.
   * Matches FastAPI endpoint: POST /api/conversations/{conversationId}/messages
   */
  async sendMessage(
    arg1: string,
    arg2?: string
  ): Promise<{ userMessage: ChatMessage; assistantMessage: ChatMessage }> {
    // Support both signatures: sendMessage(conversationId, text) and sendMessage(text)
    let conversationId: string;
    let text: string;

    if (arg2 !== undefined) {
      conversationId = arg1;
      text = arg2;
    } else {
      conversationId = localStorage.getItem(CHAT_UI_STORAGE_KEYS.ACTIVE_CONVERSATION_ID) || mockConversationsDb[0]?.id || 'conv-1';
      text = arg1;
    }

    if (!mockMessagesDb[conversationId]) {
      mockMessagesDb[conversationId] = [];
    }

    const now = new Date();
    const timestampFormatted = new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit' }).format(now);

    const userMsg: ChatMessage = {
      id: `msg-usr-${Date.now()}`,
      conversation_id: conversationId,
      role: 'user',
      sender: 'user',
      content: text,
      text,
      created_at: now.toISOString(),
      timestamp: timestampFormatted,
    };

    mockMessagesDb[conversationId] = [...mockMessagesDb[conversationId], userMsg];

    // Update conversation title automatically if it's the default "New Conversation"
    const convIndex = mockConversationsDb.findIndex((c) => c.id === conversationId);
    if (convIndex !== -1) {
      const conv = mockConversationsDb[convIndex];
      const newTitle = conv.title === 'New Conversation'
        ? text.slice(0, 36) + (text.length > 36 ? '...' : '')
        : conv.title;

      mockConversationsDb[convIndex] = {
        ...conv,
        title: newTitle,
        updated_at: now.toISOString(),
      };
    }

    await delay(750); // Simulate autonomous agent planning and tool execution

    const textLower = text.toLowerCase();
    let replyContent = "I've synthesized your workspace and context across academic and personal life.";
    let actionCard: ActionCardData | undefined = undefined;
    let steps: AgentStep[] = [
      { id: `s-${Date.now()}-1`, title: 'Parsed user intent and life domain context', status: 'completed', timestamp: 'Just now' },
      { id: `s-${Date.now()}-2`, title: 'Queried student task, calendar, and financial models', status: 'completed', timestamp: 'Just now' },
    ];

    if (textLower.includes('study plan') || textLower.includes('exam')) {
      replyContent = "I've analyzed your syllabus coverage and upcoming exam dates. Here is an optimized revision plan designed to ensure comprehensive mastery:";
      actionCard = {
        type: 'study_plan_generated',
        title: 'Study Plan: Exam Revision Sprint',
        subtitle: '4 focused sessions · 6.5 hours',
        details: {
          Subject: textLower.includes('dbms') ? 'Database Systems' : 'Machine Learning',
          Sessions: '4 Sessions Scheduled',
          TotalHours: '6.5 Hours',
          TargetGrade: 'A / 90%+',
        },
        status: 'pending',
      };
      steps.push(
        { id: `s-${Date.now()}-3`, title: 'Calculated high-priority topic weightings', status: 'completed', timestamp: 'Just now' },
        { id: `s-${Date.now()}-4`, title: 'Generated balanced 4-session study plan card', status: 'completed', timestamp: 'Just now' }
      );
    } else if (textLower.includes('bill') || textLower.includes('electricity') || textLower.includes('internet') || textLower.includes('pay')) {
      replyContent = "I checked your pending bills. You have 2 bills scheduled for this week:\n\n• **Electricity**: ₹1,200 (Due Sep 29)\n• **Fiber Internet**: ₹800 (Due Oct 1)\n\nI've generated a payment reminder card so you don't miss the deadline.";
      actionCard = {
        type: 'create_reminder',
        title: 'Electricity Bill Payment Alert',
        subtitle: 'Sep 29 · 10:00 AM',
        details: {
          Title: 'Pay Electricity Bill — ₹1,200',
          Date: new Date(Date.now() + 3 * 86400000).toISOString().split('T')[0],
          Time: '10:00',
          Category: 'Financial',
        },
        status: 'pending',
      };
      steps.push(
        { id: `s-${Date.now()}-3`, title: 'Retrieved upcoming bills from financial database', status: 'completed', timestamp: 'Just now' },
        { id: `s-${Date.now()}-4`, title: 'Drafted payment reminder action card', status: 'completed', timestamp: 'Just now' }
      );
    } else if (textLower.includes('expense') || textLower.includes('spent') || textLower.includes('budget')) {
      replyContent = "Here's your monthly spending summary:\n\n• **Food**: ₹1,170\n• **Travel**: ₹150\n• **Education**: ₹120\n\n**Total Spent**: ₹1,440. You are well within your monthly student allowance of ₹5,000.";
      steps.push(
        { id: `s-${Date.now()}-3`, title: 'Aggregated monthly transactions by category', status: 'completed', timestamp: 'Just now' },
        { id: `s-${Date.now()}-4`, title: 'Calculated budget utilization percentage (28.8%)', status: 'completed', timestamp: 'Just now' }
      );
    } else if (textLower.includes('goal') || textLower.includes('progress') || textLower.includes('internship')) {
      replyContent = "Here is the status of your top active goals:\n\n1. 🎓 **Score 90% in Machine Learning** — 75% complete\n2. 💼 **Apply to 10 Summer Internships** — 20% (2 applied)\n3. 📚 **Read 5 Non-Fiction Books** — 60% (3/5 done)\n4. 💰 **Emergency Savings Target** — 40% (₹8,000 / ₹20,000)\n\nFocus recommendation: Submit 2 internship applications before Friday.";
      steps.push(
        { id: `s-${Date.now()}-3`, title: 'Fetched active student goals & target milestones', status: 'completed', timestamp: 'Just now' },
        { id: `s-${Date.now()}-4`, title: 'Ranked goals by proximity to deadline', status: 'completed', timestamp: 'Just now' }
      );
    } else if (textLower.includes('reminder') || textLower.includes('remind') || textLower.includes('schedule')) {
      replyContent = "I've drafted a priority revision reminder based on your timeline. Please review and confirm below:";
      actionCard = {
        type: 'create_reminder',
        title: 'Priority Academic Review',
        subtitle: 'Tomorrow · 7:00 PM',
        details: {
          Title: 'Study & Review Block',
          Date: new Date(Date.now() + 86400000).toISOString().split('T')[0],
          Time: '19:00',
          Priority: 'High',
        },
        status: 'pending',
      };
      steps.push(
        { id: `s-${Date.now()}-3`, title: 'Checked calendar schedule for free slots', status: 'completed', timestamp: 'Just now' },
        { id: `s-${Date.now()}-4`, title: 'Created reminder action card for user approval', status: 'completed', timestamp: 'Just now' }
      );
    } else {
      replyContent = `Understood. I've noted that in your active context. I can help you plan study sessions, log expenses, manage bill payments, monitor goals, or prepare for exams. What would you like to tackle next?`;
      steps.push({ id: `s-${Date.now()}-3`, title: 'Synthesized context and formulated response', status: 'completed', timestamp: 'Just now' });
    }

    const assistantMsg: ChatMessage = {
      id: `msg-ast-${Date.now()}`,
      conversation_id: conversationId,
      role: 'assistant',
      sender: 'assistant',
      content: replyContent,
      text: replyContent,
      created_at: new Date().toISOString(),
      timestamp: new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit' }).format(new Date()),
      actionCard,
      metadata: {
        actionCard,
        steps,
        status: 'success',
      },
      steps,
    };

    mockMessagesDb[conversationId] = [...mockMessagesDb[conversationId], assistantMsg];

    // Log to Agent Runs execution history
    const newRun: AgentRun = {
      id: `run-${Date.now()}`,
      runNumber: `#${Math.floor(1043 + Math.random() * 50)}`,
      request: text,
      status: 'completed',
      startedAt: now.toISOString(),
      completedAt: new Date().toISOString(),
      duration: '3.4s',
      toolsUsed: steps.map((s) => s.title.split(' ')[0]),
      steps,
    };
    const currentRuns = storage.getAgentRuns();
    storage.setAgentRuns([newRun, ...currentRuns]);

    return { userMessage: userMsg, assistantMessage: assistantMsg };
  },

  /**
   * Rename a conversation title.
   * Matches FastAPI endpoint: PATCH /api/conversations/{id}
   */
  async renameConversation(id: string, title: string): Promise<Conversation> {
    await delay(100);
    const index = mockConversationsDb.findIndex((c) => c.id === id);
    if (index === -1) {
      throw new Error(`Conversation not found: ${id}`);
    }

    const updated = {
      ...mockConversationsDb[index],
      title: title.trim() || 'Untitled Conversation',
      updated_at: new Date().toISOString(),
    };
    mockConversationsDb[index] = updated;
    return updated;
  },

  /**
   * Delete a conversation and its messages.
   * Matches FastAPI endpoint: DELETE /api/conversations/{id}
   */
  async deleteConversation(id: string): Promise<void> {
    await delay(100);
    mockConversationsDb = mockConversationsDb.filter((c) => c.id !== id);
    delete mockMessagesDb[id];

    // If active conversation was deleted, switch to first available or clear
    const activeStored = localStorage.getItem(CHAT_UI_STORAGE_KEYS.ACTIVE_CONVERSATION_ID);
    if (activeStored === id) {
      const nextId = mockConversationsDb[0]?.id || '';
      if (nextId) {
        localStorage.setItem(CHAT_UI_STORAGE_KEYS.ACTIVE_CONVERSATION_ID, nextId);
      } else {
        localStorage.removeItem(CHAT_UI_STORAGE_KEYS.ACTIVE_CONVERSATION_ID);
      }
    }
  },

  /**
   * Retry a failed message within a conversation.
   */
  async retryMessage(conversationId: string, messageId: string): Promise<ChatMessage> {
    const messages = mockMessagesDb[conversationId] || [];
    const targetMsg = messages.find((m) => m.id === messageId);
    if (!targetMsg) {
      throw new Error(`Message not found: ${messageId}`);
    }
    const result = await this.sendMessage(conversationId, targetMsg.content || targetMsg.text || '');
    return result.assistantMessage;
  },

  /**
   * Handle user action card decision (Approve / Reject).
   */
  async handleActionCardDecision(messageId: string, decision: 'approved' | 'rejected'): Promise<boolean> {
    await delay(200);

    // Search across all conversation messages for this card
    for (const convId of Object.keys(mockMessagesDb)) {
      const messages = mockMessagesDb[convId];
      const targetIndex = messages.findIndex((m) => m.id === messageId);
      if (targetIndex !== -1) {
        const msg = messages[targetIndex];
        if (msg.actionCard) {
          msg.actionCard.status = decision;
          if (msg.metadata?.actionCard) {
            msg.metadata.actionCard.status = decision;
          }

          if (decision === 'approved') {
            if (msg.actionCard.type === 'create_reminder' && msg.actionCard.details) {
              await reminderService.createReminder({
                title: msg.actionCard.details.Title || msg.actionCard.title,
                date: msg.actionCard.details.Date || new Date().toISOString().split('T')[0],
                time: msg.actionCard.details.Time || '10:00',
                repeat: 'none',
                status: 'upcoming',
                category: (msg.actionCard.details.Category?.toLowerCase() as any) || 'general',
              });
            } else if (msg.actionCard.type === 'study_plan_generated') {
              await studyPlanService.createSession({
                subject: msg.actionCard.details?.Subject || 'Machine Learning',
                topic: 'Exam Preparation Block (AI Generated)',
                startTime: '16:00',
                endTime: '17:30',
                date: new Date().toISOString().split('T')[0],
                priority: 'high',
                status: 'scheduled',
              });
            }
          }
          return true;
        }
      }
    }
    return false;
  },

  /**
   * Clear current conversation history.
   */
  async clearHistory(conversationId?: string): Promise<void> {
    await delay(100);
    const id = conversationId || localStorage.getItem(CHAT_UI_STORAGE_KEYS.ACTIVE_CONVERSATION_ID) || mockConversationsDb[0]?.id;
    if (id && mockMessagesDb[id]) {
      mockMessagesDb[id] = [];
    }
  },
};
