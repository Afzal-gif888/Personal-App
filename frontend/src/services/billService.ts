import type { Bill, BillStatus } from '../types';
import { api } from './api';

interface BillOut {
  id: string;
  title: string;
  category: string;
  amount: number;
  dueDate: string;
  status: BillStatus | 'cancelled';
  recurring: boolean;
  frequency: string | null;
  paymentMethod: string | null;
  notes: string | null;
}

const toBill = (b: BillOut): Bill => ({
  id: b.id,
  title: b.title,
  amount: b.amount,
  dueDate: b.dueDate,
  category: b.category,
  status: b.status === 'cancelled' ? 'paid' : b.status,
  isRecurring: b.recurring,
  frequency: b.frequency ?? undefined,
  paymentMethod: b.paymentMethod ?? undefined,
  notes: b.notes ?? undefined,
});

function toBody(data: Partial<Bill>) {
  const body: Record<string, unknown> = {};
  if (data.title !== undefined) body.title = data.title;
  if (data.amount !== undefined) body.amount = data.amount;
  if (data.dueDate !== undefined) body.dueDate = data.dueDate;
  if (data.category !== undefined) body.category = data.category;
  if (data.isRecurring !== undefined) body.recurring = data.isRecurring;
  if (data.frequency !== undefined) body.frequency = data.frequency || null;
  if (data.paymentMethod !== undefined) body.paymentMethod = data.paymentMethod || null;
  if (data.notes !== undefined) body.notes = data.notes || null;
  return body;
}

export const billService = {
  async getBills(): Promise<Bill[]> {
    return (await api.get<BillOut[]>('/bills')).map(toBill);
  },

  // The server derives status from the due date, so it isn't sent on create.
  async createBill(data: Omit<Bill, 'id'>): Promise<Bill> {
    return toBill(await api.post<BillOut>('/bills', toBody(data)));
  },

  async updateBill(id: string, data: Partial<Bill>): Promise<Bill> {
    const body = toBody(data);
    if (data.status !== undefined) body.status = data.status;
    return toBill(await api.patch<BillOut>(`/bills/${id}`, body));
  },

  /** Records a payment; a recurring bill also gets its next bill created. */
  async markAsPaid(id: string): Promise<Bill> {
    return toBill((await api.post<{ bill: BillOut }>(`/bills/${id}/pay`)).bill);
  },

  async deleteBill(id: string): Promise<void> {
    await api.delete(`/bills/${id}`);
  },
};
