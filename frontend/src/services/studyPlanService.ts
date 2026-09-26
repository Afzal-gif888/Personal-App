import type { StudySession, StudySessionStatus } from '../types';
import { storage } from './storage';

const delay = (ms = 150) => new Promise((resolve) => setTimeout(resolve, ms));

export const studyPlanService = {
  async getStudySessions(): Promise<StudySession[]> {
    await delay(150);
    return storage.getStudySessions();
  },

  async createSession(sessionData: Omit<StudySession, 'id'>): Promise<StudySession> {
    await delay(200);
    const sessions = storage.getStudySessions();
    const newSession: StudySession = {
      ...sessionData,
      id: `plan-${Date.now()}`,
    };
    const updated = [newSession, ...sessions];
    storage.setStudySessions(updated);
    return newSession;
  },

  async updateSession(id: string, updates: Partial<StudySession>): Promise<StudySession> {
    await delay(150);
    const sessions = storage.getStudySessions();
    let updatedSession: StudySession | null = null;
    const updated = sessions.map((s) => {
      if (s.id === id) {
        updatedSession = { ...s, ...updates };
        return updatedSession;
      }
      return s;
    });
    if (!updatedSession) throw new Error(`Study session with id ${id} not found.`);
    storage.setStudySessions(updated);
    return updatedSession;
  },

  async deleteSession(id: string): Promise<void> {
    await delay(150);
    const sessions = storage.getStudySessions();
    storage.setStudySessions(sessions.filter((s) => s.id !== id));
  },

  async toggleSessionComplete(id: string): Promise<StudySession> {
    const sessions = storage.getStudySessions();
    const target = sessions.find((s) => s.id === id);
    if (!target) throw new Error(`Study session with id ${id} not found.`);
    const newStatus: StudySessionStatus = target.status === 'completed' ? 'scheduled' : 'completed';
    return this.updateSession(id, { status: newStatus });
  },

  async generateAIStudyPlan(subject: string, _targetHours: number): Promise<StudySession[]> {
    await delay(1000); // Simulate AI generation processing
    const todayStr = new Date().toISOString().split('T')[0];
    const generatedSessions: StudySession[] = [
      {
        id: `plan-ai-1-${Date.now()}`,
        subject: subject || 'Machine Learning',
        topic: 'Core Theory & Formula Proofs',
        date: todayStr,
        startTime: '16:00',
        endTime: '17:30',
        priority: 'high',
        status: 'scheduled',
        notes: 'AI generated: High leverage topic revision based on upcoming exams.',
      },
      {
        id: `plan-ai-2-${Date.now()}`,
        subject: subject || 'Machine Learning',
        topic: 'Practice Problem Solving & Code Lab',
        date: todayStr,
        startTime: '18:00',
        endTime: '19:30',
        priority: 'medium',
        status: 'scheduled',
        notes: 'AI generated: Active recall exercises.',
      },
    ];

    const currentSessions = storage.getStudySessions();
    const updated = [...generatedSessions, ...currentSessions];
    storage.setStudySessions(updated);
    return generatedSessions;
  },
};
