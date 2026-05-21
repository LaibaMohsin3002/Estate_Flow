import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckSquare, Clock, ChevronRight, CheckCircle2, AlertCircle } from 'lucide-react';
import {
  approveMaintenanceRequest,
  fetchPendingApprovals,
} from '../services/estateflow';
import { MaintenanceRequest } from '../types';
import { needsManagerApproval } from '../lib/pipeline';
import { StatusBadge } from '../components/StatusBadge';
import { UrgencyBadge } from '../components/UrgencyBadge';
import { TableSkeleton } from '../components/LoadingSkeleton';
import { EmptyState } from '../components/EmptyState';

export default function Approvals() {
  const [requests, setRequests] = useState<MaintenanceRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ id: string; message: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    loadRequests();
  }, []);

  async function loadRequests() {
    setLoading(true);
    try {
      setRequests(await fetchPendingApprovals());
    } catch {
      setRequests([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove(id: string) {
    setApproving(id);
    setFeedback(null);
    try {
      await approveMaintenanceRequest(id);
      setFeedback({ id, message: 'Approved — pipeline restarting', type: 'success' });
      setTimeout(() => loadRequests(), 1500);
    } catch (err) {
      setFeedback({ id, message: err instanceof Error ? err.message : 'Approval failed', type: 'error' });
    } finally {
      setApproving(null);
    }
  }

  const criticalRequests = requests.filter(needsManagerApproval);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Approvals</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Requests requiring manager sign-off before the AI pipeline continues.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl shadow-card border border-gray-100 p-4">
          <p className="text-xs text-gray-500">Pending Approval</p>
          <p className="text-2xl font-bold text-amber-600 mt-1">
            {requests.filter(r => r.status === 'Pending Approval').length}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-card border border-gray-100 p-4">
          <p className="text-xs text-gray-500">Critical Urgency</p>
          <p className="text-2xl font-bold text-red-600 mt-1">
            {requests.filter(r => r.maintenance_pipeline_results?.urgency === 'Critical').length}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-card border border-gray-100 p-4 col-span-2 sm:col-span-1">
          <p className="text-xs text-gray-500">Total Queue</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{criticalRequests.length}</p>
        </div>
      </div>

      {/* Queue */}
      <div className="bg-white rounded-xl shadow-card border border-gray-100 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
          <CheckSquare size={16} className="text-teal-700" />
          <h2 className="text-sm font-semibold text-gray-900">Approval Queue</h2>
        </div>

        {loading ? (
          <div className="p-5"><TableSkeleton rows={4} /></div>
        ) : criticalRequests.length === 0 ? (
          <EmptyState
            icon={<CheckCircle2 size={20} />}
            title="All clear"
            description="No requests currently require approval."
          />
        ) : (
          <div className="divide-y divide-gray-50">
            {criticalRequests.map(req => {
              const pipeline = req.maintenance_pipeline_results;
              const isApproving = approving === req.id;
              const fb = feedback?.id === req.id ? feedback : null;

              return (
                <div key={req.id} className="px-5 py-4">
                  <div className="flex items-start gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1.5">
                        <span className="text-xs font-mono text-gray-400">{req.ticket_id}</span>
                        <StatusBadge status={req.status} />
                        {pipeline?.urgency && <UrgencyBadge level={pipeline.urgency} />}
                      </div>
                      <p className="text-sm font-medium text-gray-900 mb-1">{req.original_issue}</p>
                      <p className="text-xs text-gray-500">
                        {req.property_name} · Unit {req.unit} · {req.tenant_name}
                      </p>

                      {pipeline?.summary && (
                        <p className="mt-2 text-xs text-gray-600 bg-gray-50 rounded-lg p-2.5">
                          <span className="font-medium">AI Summary: </span>{pipeline.summary}
                        </p>
                      )}

                      <div className="mt-2 flex items-center gap-3 flex-wrap text-xs text-gray-500">
                        {pipeline?.assigned_vendor && <span>Vendor: {pipeline.assigned_vendor}</span>}
                        {pipeline?.sla_target_hours != null && <span>SLA: {pipeline.sla_target_hours}h</span>}
                        {pipeline?.report_pending_signature && (
                          <span className="text-amber-600 font-medium flex items-center gap-1">
                            <Clock size={11} />
                            Report awaiting signature
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-col items-end gap-2 flex-shrink-0">
                      <Link
                        to={`/requests/${req.id}`}
                        className="text-xs text-teal-700 hover:underline flex items-center gap-1"
                      >
                        View <ChevronRight size={12} />
                      </Link>
                      <button
                        onClick={() => handleApprove(req.id)}
                        disabled={isApproving}
                        className="flex items-center gap-1.5 bg-teal-700 hover:bg-teal-800 disabled:opacity-60 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition-colors"
                      >
                        {isApproving ? (
                          <div className="w-3 h-3 border border-white/50 border-t-white rounded-full animate-spin" />
                        ) : (
                          <CheckCircle2 size={13} />
                        )}
                        {isApproving ? 'Approving…' : 'Approve'}
                      </button>
                    </div>
                  </div>

                  {fb && (
                    <div className={`mt-2 flex items-center gap-2 text-xs rounded-lg px-3 py-2 ${
                      fb.type === 'success'
                        ? 'bg-green-50 text-green-700 border border-green-200'
                        : 'bg-red-50 text-red-700 border border-red-200'
                    }`}>
                      {fb.type === 'success' ? <CheckCircle2 size={13} /> : <AlertCircle size={13} />}
                      {fb.message}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
