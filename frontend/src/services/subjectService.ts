import { api } from './api';

export interface Subject {
  id: string;
  name: string;
  code: string | null;
}

export const subjectService = {
  async getSubjects(): Promise<Subject[]> {
    return api.get<Subject[]>('/subjects');
  },
};
