import type { StudySession, StudySessionStatus } from '../types';
import { api } from './api';

interface StudySessionOut {
  id: string;
  subjectName: string | null;
  topic: string;
  description: string | null;
  date: string;
  startTime: string;
  endTime: string;
  priority: StudySession['priority'];
  status: StudySessionStatus | 'missed';
}

const toSession = (s: StudySessionOut): StudySession => ({
  id: s.id,
  subject: s.subjectName ?? '',
  topic: s.topic,
  date: s.date,
  startTime: s.startTime,
  endTime: s.endTime,
  priority: s.priority,
  status: s.status === 'missed' ? 'cancelled' : s.status,
  notes: s.description ?? undefined,
});

function toBody(data: Partial<StudySession>) {
  const body: Record<string, unknown> = {};
  if (data.subject !== undefined) body.subjectName = data.subject || null;
  if (data.topic !== undefined) body.topic = data.topic;
  if (data.notes !== undefined) body.description = data.notes || null;
  if (data.date !== undefined) body.date = data.date;
  if (data.startTime !== undefined) body.startTime = data.startTime;
  if (data.endTime !== undefined) body.endTime = data.endTime;
  if (data.priority !== undefined) body.priority = data.priority;
  if (data.status !== undefined) body.status = data.status;
  return body;
}

export const studyPlanService = {
  async getStudySessions(): Promise<StudySession[]> {
    return (await api.get<StudySessionOut[]>('/study-sessions')).map(toSession);
  },

  async createSession(data: Omit<StudySession, 'id'>): Promise<StudySession> {
    return toSession(await api.post<StudySessionOut>('/study-sessions', toBody(data)));
  },

  async updateSession(id: string, updates: Partial<StudySession>): Promise<StudySession> {
    return toSession(await api.patch<StudySessionOut>(`/study-sessions/${id}`, toBody(updates)));
  },

  async deleteSession(id: string): Promise<void> {
    await api.delete(`/study-sessions/${id}`);
  },

  async toggleSessionComplete(id: string): Promise<StudySession> {
    const sessions = await studyPlanService.getStudySessions();
    const current = sessions.find((s) => s.id === id);
    return studyPlanService.updateSession(id, { status: current?.status === 'completed' ? 'scheduled' : 'completed' });
  },

  /** Server-side plan generator: spreads sessions over the next days inside the preferred study window. */
  async generateAIStudyPlan(subject: string, targetHours: number): Promise<StudySession[]> {
    const minutesPerDay = Math.min(600, Math.max(15, Math.round((targetHours || 1.5) * 60)));
    const plan = await api.post<{ sessions: StudySessionOut[] }>('/study-plans/generate', {
      subject: subject || 'General revision',
      minutesPerDay,
    });
    return plan.sessions.map(toSession);
  },
};
