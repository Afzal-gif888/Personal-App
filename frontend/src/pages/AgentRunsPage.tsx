import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, ChevronRight } from 'lucide-react';
import { useAgentRuns } from '../hooks/useAgentRuns';
import { Page, PageHeader } from '../components/ui/PageHeader';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { StatCard } from '../components/ui/StatCard';
import { StatGrid, DesktopOnly, MobileList, MobileRow } from '../components/ui/ResponsiveList';
import { EmptyState } from '../components/ui/EmptyState';
import { Table, THead, TBody, TR, TH, TD } from '../components/ui/Table';
import { Toolbar, SearchField, TableFooter } from '../components/ui/Toolbar';
import { formatRelativeTime } from '../utils/formatters';
import { RUN_STATUS_STYLES, statusStyle } from '../utils/status';

export const AgentRunsPage: React.FC = () => {
  const { agentRuns } = useAgentRuns();
  const navigate = useNavigate();
  const [search, setSearch] = useState('');

  const q = search.trim().toLowerCase();
  const runs = [...agentRuns]
    .sort((a, b) => b.startedAt.localeCompare(a.startedAt))
    .filter((r) => !q || r.request.toLowerCase().includes(q) || r.runNumber.includes(q));

  const completed = agentRuns.filter((r) => r.status === 'completed').length;
  const totalSteps = agentRuns.reduce((s, r) => s + r.steps.length, 0);
  const openRun = (id: string) => navigate(`/agent-runs/${id.replace('run-', '')}`);

  return (
    <Page>
      <PageHeader
        title="Agent activity"
        description="An audit log of every assistant run: what was asked, which tools ran, and what came back."
      />

      <StatGrid cols={3}>
        <StatCard label="Total runs" value={agentRuns.length} hint="Since workspace creation" />
        <StatCard
          label="Success rate"
          value={agentRuns.length ? `${Math.round((completed / agentRuns.length) * 100)}%` : '—'}
          hint={`${completed} completed`}
          tone="success"
        />
        <StatCard label="Tool calls" value={totalSteps} hint="Across all runs" />
      </StatGrid>

      <Toolbar>
        <SearchField value={search} onChange={setSearch} placeholder="Search requests or run #" />
      </Toolbar>

      <Card flush className="overflow-hidden">
        {runs.length === 0 ? (
          <EmptyState
            bare
            icon={<Activity />}
            title={q ? 'No matching runs' : 'No runs yet'}
            description={q ? 'Try a different search.' : 'Runs appear here each time you send the assistant a request.'}
          />
        ) : (
          <>
            <MobileList>
              {runs.map((run) => {
                const s = statusStyle(RUN_STATUS_STYLES, run.status);
                return (
                  <MobileRow
                    key={run.id}
                    onClick={() => openRun(run.id)}
                    title={run.request}
                    subtitle={`${run.runNumber} · ${run.toolsUsed.length} tools · ${run.duration} · ${formatRelativeTime(run.startedAt)}`}
                    meta={
                      <Badge variant={s.variant} dot>
                        {s.label}
                      </Badge>
                    }
                    actions={<ChevronRight className="size-4 text-fg-faint mt-2 mr-1.5" />}
                  />
                );
              })}
            </MobileList>
            <DesktopOnly>
            <Table>
              <THead>
                <tr>
                  <TH className="w-24">Run</TH>
                  <TH>Request</TH>
                  <TH>Status</TH>
                  <TH className="hidden lg:table-cell">Tools</TH>
                  <TH className="hidden md:table-cell text-right">Duration</TH>
                  <TH className="hidden sm:table-cell">Started</TH>
                  <TH className="w-10" />
                </tr>
              </THead>
              <TBody>
                {runs.map((run) => {
                  const s = statusStyle(RUN_STATUS_STYLES, run.status);
                  return (
                    <TR key={run.id} interactive onClick={() => openRun(run.id)}>
                      <TD className="font-mono text-xs text-fg-muted">{run.runNumber}</TD>
                      <TD className="w-full max-w-0">
                        <p className="font-medium truncate">{run.request}</p>
                        <p className="text-xs text-fg-subtle mt-0.5">{run.toolsUsed.length} tools</p>
                      </TD>
                      <TD>
                        <Badge variant={s.variant} dot>
                          {s.label}
                        </Badge>
                      </TD>
                      <TD className="hidden lg:table-cell">
                        <div className="flex items-center gap-1 max-w-xs overflow-hidden">
                          {run.toolsUsed.slice(0, 2).map((tool, i) => (
                            <code
                              key={i}
                              className="shrink-0 font-mono text-2xs text-fg-muted bg-subtle border border-line rounded px-1.5 py-0.5"
                            >
                              {tool}
                            </code>
                          ))}
                          {run.toolsUsed.length > 2 && (
                            <span className="text-xs text-fg-faint shrink-0">+{run.toolsUsed.length - 2}</span>
                          )}
                        </div>
                      </TD>
                      <TD className="hidden md:table-cell text-right font-mono text-xs text-fg-muted">{run.duration}</TD>
                      <TD className="hidden sm:table-cell text-fg-muted whitespace-nowrap">{formatRelativeTime(run.startedAt)}</TD>
                      <TD>
                        <ChevronRight className="size-4 text-fg-faint" />
                      </TD>
                    </TR>
                  );
                })}
              </TBody>
            </Table>
            </DesktopOnly>
            <TableFooter shown={runs.length} total={agentRuns.length} noun="runs" />
          </>
        )}
      </Card>
    </Page>
  );
};
