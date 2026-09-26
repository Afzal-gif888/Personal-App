import type { Bill } from '../types';
import { storage } from './storage';

const delay = (ms = 150) => new Promise((resolve) => setTimeout(resolve, ms));

export const billService = {
  async getBills(): Promise<Bill[]> {
    await delay(150);
    return storage.getBills();
  },

  async createBill(data: Omit<Bill, 'id'>): Promise<Bill> {
    await delay(200);
    const bills = storage.getBills();
    const newBill: Bill = { ...data, id: `bill-${Date.now()}` };
    storage.setBills([...bills, newBill]);
    return newBill;
  },

  async updateBill(id: string, data: Partial<Bill>): Promise<Bill> {
    await delay(200);
    const bills = storage.getBills();
    const updated = bills.map((b) => (b.id === id ? { ...b, ...data } : b));
    storage.setBills(updated);
    const found = updated.find((b) => b.id === id);
    if (!found) throw new Error('Bill not found');
    return found;
  },

  async markAsPaid(id: string): Promise<Bill> {
    return billService.updateBill(id, { status: 'paid' });
  },

  async deleteBill(id: string): Promise<void> {
    await delay(150);
    storage.setBills(storage.getBills().filter((b) => b.id !== id));
  },
};
