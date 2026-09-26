import type { Expense } from '../types';

export const INITIAL_EXPENSES: Expense[] = [
  {
    id: 'exp-1',
    title: 'Groceries',
    amount: 850,
    category: 'Food',
    date: '2026-09-25',
    description: 'Weekly grocery run at Supermart',
  },
  {
    id: 'exp-2',
    title: 'Uber to College',
    amount: 150,
    category: 'Travel',
    date: '2026-09-24',
    description: 'Late for morning lecture',
  },
  {
    id: 'exp-3',
    title: 'Cafe Coffee Day',
    amount: 320,
    category: 'Food',
    date: '2026-09-23',
    description: 'Study session coffee',
  },
  {
    id: 'exp-4',
    title: 'Stationery',
    amount: 120,
    category: 'Education',
    date: '2026-09-20',
    description: 'Notebooks and pens',
  }
];
