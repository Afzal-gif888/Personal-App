import type { ApprovalAction } from '../types';
import { storage } from './storage';
import { reminderService } from './reminderService';
import { taskService } from './taskService';

const delay = (ms = 150) => new Promise((resolve) => setTimeout(resolve, ms));

export const approvalService = {
  async getApprovals(): Promise<ApprovalAction[]> {
    await delay(150);
    return storage.getApprovals();
  },

  async respondToApproval(id: string, decision: 'approved' | 'rejected'): Promise<ApprovalAction> {
    await delay(200);
    const approvals = storage.getApprovals();
    const target = approvals.find((a) => a.id === id);
    if (!target) throw new Error(`Approval action with id ${id} not found.`);

    const updatedAction: ApprovalAction = {
      ...target,
      status: decision,
      respondedAt: new Date().toISOString(),
    };

    const updated = approvals.map((a) => (a.id === id ? updatedAction : a));
    storage.setApprovals(updated);

    // If approved, trigger corresponding mock side-effect in application state!
    if (decision === 'approved') {
      if (target.type.toLowerCase().includes('reminder')) {
        await reminderService.createReminder({
          title: target.title.replace('Schedule ', '').replace('Create ', ''),
          description: target.description,
          date: target.details['Date'] || new Date().toISOString().split('T')[0],
          time: target.details['Time'] || '19:00',
          repeat: 'none',
          status: 'upcoming',
        });
      } else if (target.type.toLowerCase().includes('task')) {
        await taskService.createTask({
          title: target.title,
          description: target.description,
          category: (target.details['Category']?.toLowerCase() as any) || 'general',
          subject: target.details['Subject'] || undefined,
          priority: (target.details['Priority']?.toLowerCase() as any) || 'high',
          dueDate: target.details['DueDate'] || new Date().toISOString().split('T')[0],
          dueTime: target.details['DueTime'] || '17:00',
          status: 'pending',
        });
      }
    }

    return updatedAction;
  },
};
