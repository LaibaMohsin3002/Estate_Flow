import { useEffect, useState, useCallback } from 'react';
import {
  Shield, MessageSquare, AlertTriangle, Scale, MapPin,
  UserCheck, Calendar, Bell, FileText, BarChart2,
  CheckCircle2, XCircle, Loader2, Clock
} from 'lucide-react';
import { fetchPipelineLive } from '../services/estateflow';
import { AgentLog, AgentStep, AgentStepStatus, PipelineResult } from '../types';
import { isPipelineComplete } from '../constants/pipeline';

const AGENT_DEFINITIONS = [
  { key: 'security_agent', label: 'Security Agent', description: 'RBAC, PII redaction, injection scan', icon: Shield },
  { key: 'complaint_agent', label: 'Complaint Agent', description: 'Parse EN/Urdu/Roman Urdu', icon: MessageSquare },
  { key: 'priority_agent', label: 'Priority Agent', description: 'Risk matrix + urgency scoring', icon: AlertTriangle },
  { key: 'compliance_agent', label: 'Compliance Agent', description: 'SLA flags & regulatory check', icon: Scale },
  { key: 'vendor_matching_agent', label: 'Vendor Matching', description: 'Nearest vendor by geolocation', icon: MapPin },
  { key: 'governance_ethics_agent', label: 'Governance & Ethics', description: 'Human approval gate', icon: UserCheck },
  { key: 'scheduling_agent', label: 'Scheduling Agent', description: 'Book work slot', icon: Calendar },
  { key: 'communications_agent', label: 'Communications', description: 'Tenant & manager notifications', icon: Bell },
  { key: 'report_agent', label: 'Report Agent', description: 'PDF, audit ledger, manager signature', icon: FileText },
  { key: 'performance_agent', label: 'Performance Agent', description: 'Latency, tokens, alerts', icon: BarChart2 },
];

function buildSteps(
  agentLogs: AgentLog[],
  requestStatus: string
): AgentStep[] {
  const logMap = new Map(agentLogs.map((l) => [l.agent_name, l]));
  const pipelineDone = isPipelineComplete(
    agentLogs.map((l) => l.agent_name),
    requestStatus
  );

  let foundRunning = false;

  return AGENT_DEFINITIONS.map((def) => {
    const log = logMap.get(def.key);
    let status: AgentStepStatus = 'pending';

    if (log) {
      status = log.success ? 'done' : 'failed';
    } else if (!pipelineDone && !foundRunning) {
      status = 'running';
      foundRunning = true;
    }

    if (requestStatus === 'Blocked' && def.key === 'security_agent' && !log?.success) {
      status = 'failed';
    }

    return {
      key: def.key,
      label: def.label,
      description: def.description,
      status,
      duration_ms: log?.duration_ms,
      output: log?.output,
    };
  });
}

interface Props {
  requestId: string;
  live?: boolean;
}

export function AgentPipelineLive({ requestId, live = false }: Props) {
  const [status, setStatus] = useState('');
  const [pipeline, setPipeline] = useState<PipelineResult | undefined>();
  const [steps, setSteps] = useState<AgentStep[]>(
    AGENT_DEFINITIONS.map((d) => ({ ...d, status: 'pending' as AgentStepStatus }))
  );
  const [collapsed, setCollapsed] = useState(false);
  const [done, setDone] = useState(false);
  const [confetti, setConfetti] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const { request, pipeline: pl, agentLogs } = await fetchPipelineLive(requestId);
      setStatus(request.status);
      setPipeline(pl);
      const newSteps = buildSteps(agentLogs, request.status);
      setSteps(newSteps);

      const complete = isPipelineComplete(
        agentLogs.map((l) => l.agent_name),
        request.status
      );
      if (complete) {
        setDone(true);
        if (agentLogs.some((l) => l.agent_name === 'performance_agent' && l.success)) {
          setConfetti(true);
          setTimeout(() => setConfetti(false), 3000);
        }
      }
      return complete;
    } catch {
      return false;
    }
  }, [requestId]);

  useEffect(() => {
    refresh();
    if (!live) return;

    const interval = setInterval(async () => {
      const stop = await refresh();
      if (stop) clearInterval(interval);
    }, 800);

    return () => clearInterval(interval);
  }, [refresh, live]);

  const doneCount = steps.filter((s) => s.status === 'done').length;
  const progress = Math.round((doneCount / steps.length) * 100);

  return (
    <div
      className={`bg-white rounded-xl shadow-card border border-gray-100 overflow-hidden transition-all ${confetti ? 'ring-2 ring-green-400' : ''}`}
    >
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-gray-900">AI Agent Pipeline</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            {done
              ? `Complete — ${doneCount}/${steps.length} agents`
              : live
                ? 'Processing…'
                : `${doneCount}/${steps.length} agents`}
          </p>
        </div>
        <button
          onClick={() => setCollapsed((v) => !v)}
          className="text-xs text-gray-500 hover:text-gray-700 transition-colors"
        >
          {collapsed ? 'Expand' : 'Collapse'}
        </button>
      </div>

      <div className="h-1.5 bg-gray-100">
        <div
          className="h-full bg-teal-600 transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>

      {!collapsed && (
        <div className="px-5 py-4">
          <div className="space-y-1">
            {steps.map((step, idx) => {
              const def = AGENT_DEFINITIONS[idx];
              const Icon = def.icon;
              return (
                <div
                  key={step.key}
                  className={`flex items-start gap-3 p-2.5 rounded-lg transition-colors ${
                    step.status === 'running'
                      ? 'bg-teal-50 border border-teal-100'
                      : 'hover:bg-gray-50'
                  }`}
                >
                  <div className="flex-shrink-0 mt-0.5">
                    {step.status === 'done' && (
                      <CheckCircle2 size={18} className="text-green-500" />
                    )}
                    {step.status === 'failed' && (
                      <XCircle size={18} className="text-red-500" />
                    )}
                    {step.status === 'running' && (
                      <Loader2 size={18} className="text-teal-600 animate-spin" />
                    )}
                    {step.status === 'pending' && (
                      <div className="w-[18px] h-[18px] rounded-full border-2 border-gray-200 flex items-center justify-center">
                        <span className="text-[9px] font-semibold text-gray-400">
                          {idx + 1}
                        </span>
                      </div>
                    )}
                  </div>
                  <div
                    className={`flex-shrink-0 p-1 rounded ${
                      step.status === 'done'
                        ? 'text-green-600'
                        : step.status === 'running'
                          ? 'text-teal-600'
                          : 'text-gray-300'
                    }`}
                  >
                    <Icon size={14} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <p
                        className={`text-sm font-medium ${step.status === 'pending' ? 'text-gray-400' : 'text-gray-900'}`}
                      >
                        {step.label}
                      </p>
                      {step.duration_ms != null && (
                        <span className="text-xs text-gray-400 flex items-center gap-1">
                          <Clock size={10} />
                          {(step.duration_ms / 1000).toFixed(2)}s
                        </span>
                      )}
                    </div>
                    <p
                      className={`text-xs mt-0.5 ${step.status === 'pending' ? 'text-gray-300' : 'text-gray-500'}`}
                    >
                      {step.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {pipeline && (
            <div className="mt-4 pt-4 border-t border-gray-100 space-y-3">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                AI Outcome
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {pipeline.urgency && (
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-xs text-gray-400">Urgency</p>
                    <p className="text-sm font-semibold text-gray-900 mt-0.5">
                      {pipeline.urgency}
                    </p>
                  </div>
                )}
                {pipeline.category && (
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-xs text-gray-400">Category</p>
                    <p className="text-sm font-semibold text-gray-900 mt-0.5">
                      {pipeline.category}
                    </p>
                  </div>
                )}
                {pipeline.assigned_vendor && (
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-xs text-gray-400">Vendor</p>
                    <p className="text-sm font-semibold text-gray-900 mt-0.5">
                      {pipeline.assigned_vendor}
                    </p>
                  </div>
                )}
              </div>
              {pipeline.summary && (
                <div className="bg-teal-50 border border-teal-100 rounded-lg p-3">
                  <p className="text-xs font-medium text-teal-700 mb-1">Executive Summary</p>
                  <p className="text-sm text-teal-900">{pipeline.summary}</p>
                </div>
              )}
              {status === 'Pending Approval' && (
                <p className="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
                  Waiting for manager approval — see Approvals tab to sign and continue.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
