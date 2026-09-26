import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, ChevronDown, ChevronRight, Code } from 'lucide-react';
import { useAgentRunDetail } from '../hooks/useAgentRuns';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { formatDate } from '../utils/formatters';

export const AgentRunDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { run, isLoading } = useAgentRunDetail(id || '');
  const [expandedStepId, setExpandedStepId] = useState<string | null>(null);

  if (isLoading) {
    return <div className="p-8 text-xs text-[#8A8A8A]">Loading execution details...</div>;
  }

  if (!run) {
    return (
      <div className="space-y-4 text-left">
        <Link to="/agent-runs" className="inline-flex items-center gap-1 text-xs text-[#666666] hover:text-black">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Agent Runs
        </Link>
        <p className="text-xs text-[#8A8A8A]">Agent run record not found.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 text-left max-w-4xl">
      {/* Back Link */}
      <Link
        to="/agent-runs"
        className="inline-flex items-center gap-1.5 text-xs font-medium text-[#666666] hover:text-[#111111]"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        Back to Agent Runs
      </Link>

      {/* Header Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#EAEAEA]">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-[#111111]">Agent Run {run.runNumber}</h1>
            <Badge variant="success" size="sm">
              {run.status}
            </Badge>
          </div>
          <p className="text-xs text-[#666666]">Request: "{run.request}"</p>
        </div>

        <div className="flex items-center gap-4 text-xs text-[#8A8A8A]">
          <div>
            Duration: <span className="font-mono font-semibold text-[#111111]">{run.duration}</span>
          </div>
          <div>
            Started: <span className="font-semibold text-[#111111]">{formatDate(run.startedAt)}</span>
          </div>
        </div>
      </div>

      {/* Visual Execution Timeline */}
      <Card>
        <CardHeader>
          <CardTitle>Execution Trace & Timeline</CardTitle>
          <CardDescription>Step-by-step reasoning steps and tool execution flow</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* User Request Node */}
          <div className="relative pl-6 pb-4 border-l-2 border-black">
            <div className="absolute -left-2.5 top-0 w-4 h-4 rounded-full bg-black text-white flex items-center justify-center text-[10px] font-bold">
              ✓
            </div>
            <div className="text-xs font-semibold text-[#111111]">User Request Initiated</div>
            <p className="text-xs text-[#666666] mt-0.5">{run.request}</p>
          </div>

          {/* Steps Timeline Nodes */}
          {run.steps.map((step, idx) => {
            const isExpanded = expandedStepId === step.id;
            const isLast = idx === run.steps.length - 1;

            return (
              <div
                key={step.id}
                className={`relative pl-6 ${!isLast ? 'pb-6 border-l-2 border-[#EAEAEA]' : ''}`}
              >
                <div className="absolute -left-2.5 top-0 w-4 h-4 rounded-full bg-emerald-600 text-white flex items-center justify-center text-[10px] font-bold">
                  ✓
                </div>

                <div className="space-y-2">
                  <div
                    onClick={() => setExpandedStepId(isExpanded ? null : step.id)}
                    className="flex items-center justify-between p-3 rounded-md border border-[#EAEAEA] bg-white hover:bg-[#F7F7F7] cursor-pointer transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-[#111111]">{step.title}</span>
                      {step.toolName && (
                        <span className="font-mono text-[10px] bg-[#F7F7F7] px-2 py-0.5 rounded border border-[#EAEAEA] text-[#111111]">
                          {step.toolName}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2 text-xs text-[#8A8A8A]">
                      <span className="font-mono text-[11px]">{step.timestamp}</span>
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-[#111111]" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-[#8A8A8A]" />
                      )}
                    </div>
                  </div>

                  {/* Expandable Input / Output Details */}
                  {isExpanded && (step.toolInput || step.toolOutput) && (
                    <div className="p-3.5 rounded-md border border-[#EAEAEA] bg-[#F7F7F7] space-y-3 animate-in fade-in duration-150">
                      {step.toolInput && (
                        <div className="space-y-1">
                          <span className="text-[11px] font-semibold text-[#111111] uppercase tracking-wider flex items-center gap-1">
                            <Code className="w-3 h-3 text-[#8A8A8A]" /> Input Parameters
                          </span>
                          <pre className="text-[11px] font-mono p-2.5 rounded bg-white border border-[#EAEAEA] text-[#111111] overflow-x-auto">
                            {JSON.stringify(step.toolInput, null, 2)}
                          </pre>
                        </div>
                      )}

                      {step.toolOutput && (
                        <div className="space-y-1">
                          <span className="text-[11px] font-semibold text-[#111111] uppercase tracking-wider flex items-center gap-1">
                            <Code className="w-3 h-3 text-emerald-600" /> Output Payload
                          </span>
                          <pre className="text-[11px] font-mono p-2.5 rounded bg-white border border-[#EAEAEA] text-[#111111] overflow-x-auto">
                            {JSON.stringify(step.toolOutput, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
};
