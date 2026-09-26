import type { StudySession } from '../types';

export const INITIAL_STUDY_SESSIONS: StudySession[] = [
  {
    id: 'plan-1',
    subject: 'Machine Learning',
    topic: 'Regression & Convex Optimization',
    date: '2026-09-26',
    startTime: '18:00',
    endTime: '19:15',
    priority: 'high',
    status: 'scheduled',
    notes: 'Focus on L1/L2 regularization math proofs and loss minimization.',
  },
  {
    id: 'plan-2',
    subject: 'Database Systems',
    topic: 'Relational Normalization & BCNF',
    date: '2026-09-26',
    startTime: '19:30',
    endTime: '20:45',
    priority: 'high',
    status: 'scheduled',
    notes: 'Solve functional dependency closure exercises.',
  },
  {
    id: 'plan-3',
    subject: 'Operating Systems',
    topic: 'Page Replacement Algorithms (LRU/Clock)',
    date: '2026-09-26',
    startTime: '21:00',
    endTime: '22:15',
    priority: 'medium',
    status: 'completed',
    notes: 'Simulate LRU cache page faults with sample reference string.',
  },
];
