import type { ApprovalAction } from '../types';

export const INITIAL_APPROVALS: ApprovalAction[] = [
  {
    id: 'appr-1',
    runId: 'run-1043',
    type: 'Create Reminder',
    title: 'Schedule Machine Learning Revision',
    description: 'Set a priority reminder for ML Problem Set 4 derive optimization formulas.',
    details: {
      Subject: 'Machine Learning',
      Date: 'September 28, 2026',
      Time: '07:00 PM',
      Repeat: 'None',
      Priority: 'High',
    },
    status: 'pending',
    requestedAt: '2026-09-26T01:30:00Z',
  },
  {
    id: 'appr-2',
    runId: 'run-1041',
    type: 'Create Task',
    title: 'Add DBMS Indexing Milestone 2 Task',
    description: 'Auto-schedule task for DBMS B+ Tree Indexing implementation due Sep 29.',
    details: {
      Subject: 'Database Systems',
      DueDate: 'September 29, 2026',
      DueTime: '05:00 PM',
      Priority: 'High',
    },
    status: 'pending',
    requestedAt: '2026-09-25T16:45:00Z',
  },
];
