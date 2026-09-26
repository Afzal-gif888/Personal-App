import type { AgentRun } from '../types';
import { storage } from './storage';

const delay = (ms = 150) => new Promise((resolve) => setTimeout(resolve, ms));

export const agentRunService = {
  async getAgentRuns(): Promise<AgentRun[]> {
    await delay(150);
    return storage.getAgentRuns();
  },

  async getAgentRunById(id: string): Promise<AgentRun | undefined> {
    await delay(100);
    const runs = storage.getAgentRuns();
    return runs.find((r) => r.id === id || r.id === `run-${id}` || r.runNumber === `#${id}`);
  },

  async addAgentRun(run: AgentRun): Promise<AgentRun> {
    await delay(100);
    const runs = storage.getAgentRuns();
    const updated = [run, ...runs];
    storage.setAgentRuns(updated);
    return run;
  },
};
