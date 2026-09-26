import type { Goal } from '../types';

export const INITIAL_GOALS: Goal[] = [
  {
    id: 'goal-1',
    title: 'Score 90% in Machine Learning',
    category: 'academic',
    target: '90%',
    progress: 75,
    deadline: '2026-12-15',
    status: 'active',
  },
  {
    id: 'goal-2',
    title: 'Save for Summer Trip',
    category: 'financial',
    target: '₹20,000',
    progress: 40,
    deadline: '2027-05-01',
    status: 'active',
  },
  {
    id: 'goal-3',
    title: 'Apply to 10 Internships',
    category: 'career',
    target: '10 Applications',
    progress: 20, // 2/10
    deadline: '2026-11-30',
    status: 'active',
  },
  {
    id: 'goal-4',
    title: 'Read 5 non-fiction books',
    category: 'personal',
    target: '5 Books',
    progress: 60, // 3/5
    deadline: '2026-12-31',
    status: 'active',
  }
];
