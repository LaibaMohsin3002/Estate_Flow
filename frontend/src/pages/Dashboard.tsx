import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ClipboardList, Clock, CheckCircle2, AlertTriangle,
  Plus, ChevronRight, RefreshCw, TrendingUp
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import {
  fetchMaintenanceRequests,
  fetchPredictiveMaintenance,
  runPredictiveMaintenance,
} from '../services/estateflow';
import { MaintenanceRequest, PredictiveMaintenance } from '../types';
import { needsManagerApproval } from '../lib/pipeline';
import { StatusBadge } from '../components/StatusBadge';
import { UrgencyBadge } from '../components/UrgencyBadge';
import { StatCard } from '../components/StatCard';
import { TableSkeleton, CardSkeleton } from '../components/LoadingSkeleton';
import { EmptyState } from '../components/EmptyState';

export default function Dashboard() {
  const { role, user } = useAuth();

  if (role === 'tenant') return <TenantDashboard userId={user?.id} />;
  return <ManagerDashboard />;
}

function TenantDashboard({ userId }: { userId?: string }) {
  const [requests, setRequests] = useState<MaintenanceRequest[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMaintenanceRequests()
      .then(setRequests)
      .catch(() => setRequests([]))
      .finally(() => setLoading(false));
  }, [userId]);

  const open = requests.filter(r => r.status === 'Open').length;
  const inProgress = requests.filter(r => r.status === 'In Progress').length;
  const resolved = requests.filter(r => r.status === 'Resolved').length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">My Requests</h1>
          <p className="text-sm text-gray-500 mt-0.5">Track your maintenance requests</p>
        </div>
        <Link
          to="/submit"
          className="flex items-center gap-2 bg-teal-700 hover:bg-teal-800 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          <Plus size={16} />
          New Request
        </Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard label="Open" value={open} icon={<Clock size={18} />} color="amber" />
        <StatCard label="In Progress" value={inProgress} icon={<ClipboardList size={18} />} color="teal" />
        <StatCard label="Resolved" value={resolved} icon={<CheckCircle2 size={18} />} color="green" />
      </div>

      <div className="bg-white rounded-xl shadow-card border border-gray-100 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="text-sm font-semibold text-gray-900">Recent Requests</h2>
        </div>
        {loading ? (
          <div className="p-5"><TableSkeleton /></div>
        ) : requests.length === 0 ? (
          <EmptyState
            icon={<ClipboardList size={20} />}
            title="No requests yet"
            description="Submit your first maintenance request to get started."
            action={
              <Link to="/submit" className="text-sm text-teal-700 font-medium hover:underline">
                Submit a request
              </Link>
            }
          />
        ) : (
          <div className="divide-y divide-gray-50">
            {requests.map(req => (
              <Link
                key={req.id}
                to={`/requests/${req.id}`}
                className="flex items-center gap-4 px-5 py-3.5 hover:bg-gray-50 transition-colors group"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-mono text-gray-400">{req.ticket_id}</span>
                    <StatusBadge status={req.status} />
                    {req.maintenance_pipeline_results?.urgency && (
                      <UrgencyBadge level={req.maintenance_pipeline_results.urgency} />
                    )}
                  </div>
                  <p className="text-sm text-gray-900 font-medium mt-1 truncate">{req.original_issue}</p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {req.property_name} · Unit {req.unit} · {new Date(req.created_at).toLocaleDateString()}
                  </p>
                </div>
                <ChevronRight size={16} className="text-gray-300 group-hover:text-gray-400 flex-shrink-0 transition-colors" />
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ManagerDashboard() {
  const [requests, setRequests] = useState<MaintenanceRequest[]>([]);
  const [predictive, setPredictive] = useState<PredictiveMaintenance[]>([]);
  const [loadingRequests, setLoadingRequests] = useState(true);
  const [loadingPredictive, setLoadingPredictive] = useState(true);
  const [runningForecast, setRunningForecast] = useState(false);

  useEffect(() => {
    fetchMaintenanceRequests()
      .then(setRequests)
      .catch(() => setRequests([]))
      .finally(() => setLoadingRequests(false));

    fetchPredictiveMaintenance()
      .then(setPredictive)
      .catch(() => setPredictive([]))
      .finally(() => setLoadingPredictive(false));
  }, []);

  async function runForecast() {
    setRunningForecast(true);
    try {
      await runPredictiveMaintenance();
      setPredictive(await fetchPredictiveMaintenance());
    } finally {
      setRunningForecast(false);
    }
  }

  const approvalCount = requests.filter(needsManagerApproval).length;

  const critical = requests.filter(r => r.maintenance_pipeline_results?.urgency === 'Critical').length;
  const pending = requests.filter(r => r.status === 'Pending Approval').length;
  const inProgress = requests.filter(r => r.status === 'In Progress').length;
  const resolved = requests.filter(r => r.status === 'Resolved').length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Manager Dashboard</h1>
        <p className="text-sm text-gray-500 mt-0.5">Property operations overview</p>
        {approvalCount > 0 && (
          <p className="text-sm text-amber-700 mt-2">
            <Link to="/approvals" className="font-medium underline">
              {approvalCount} request(s) need your approval →
            </Link>
          </p>
        )}
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Critical" value={critical} icon={<AlertTriangle size={18} />} color="red" />
        <StatCard label="Pending Approval" value={pending} icon={<Clock size={18} />} color="amber" />
        <StatCard label="In Progress" value={inProgress} icon={<ClipboardList size={18} />} color="teal" />
        <StatCard label="Resolved" value={resolved} icon={<CheckCircle2 size={18} />} color="green" />
      </div>

      {/* Predictive maintenance */}
      <div className="bg-white rounded-xl shadow-card border border-gray-100 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp size={16} className="text-teal-700" />
            <h2 className="text-sm font-semibold text-gray-900">Predictive Maintenance Forecasts</h2>
            <span className="text-xs bg-teal-50 text-teal-700 px-2 py-0.5 rounded-full border border-teal-100">Weekly</span>
          </div>
          <button
            onClick={runForecast}
            disabled={runningForecast}
            className="flex items-center gap-1.5 text-xs text-teal-700 hover:text-teal-800 font-medium disabled:opacity-50 transition-colors"
          >
            <RefreshCw size={13} className={runningForecast ? 'animate-spin' : ''} />
            {runningForecast ? 'Running…' : 'Run now'}
          </button>
        </div>
        {loadingPredictive ? (
          <div className="p-5"><CardSkeleton /></div>
        ) : predictive.length === 0 ? (
          <EmptyState
            icon={<TrendingUp size={20} />}
            title="No forecasts available"
            description="Run the predictive maintenance engine to generate property risk forecasts."
          />
        ) : (
          <div className="divide-y divide-gray-50">
            {predictive.map(p => (
              <div key={p.property_id} className="px-5 py-3.5 flex items-center gap-4">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900">{p.property_name}</p>
                  {p.next_predicted_issue && (
                    <p className="text-xs text-gray-500 mt-0.5">Next issue: {p.next_predicted_issue}</p>
                  )}
                </div>
                <div className="text-right flex-shrink-0">
                  <div className={`text-sm font-bold ${p.risk_score >= 0.7 ? 'text-red-600' : p.risk_score >= 0.4 ? 'text-amber-600' : 'text-green-600'}`}>
                    {Math.round(p.risk_score * 100)}% risk
                  </div>
                  <p className="text-xs text-gray-400">{p.recurring_patterns_count} patterns</p>
                </div>
                <div className="w-24 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${p.risk_score >= 0.7 ? 'bg-red-500' : p.risk_score >= 0.4 ? 'bg-amber-500' : 'bg-green-500'}`}
                    style={{ width: `${Math.round(p.risk_score * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Requests table */}
      <div className="bg-white rounded-xl shadow-card border border-gray-100 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-900">All Maintenance Requests</h2>
          <Link to="/approvals" className="text-xs text-teal-700 font-medium hover:underline">
            View approvals
          </Link>
        </div>
        {loadingRequests ? (
          <div className="p-5"><TableSkeleton rows={6} /></div>
        ) : requests.length === 0 ? (
          <EmptyState
            icon={<ClipboardList size={20} />}
            title="No requests"
            description="Tenant requests will appear here."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left text-xs font-medium text-gray-500 px-5 py-3">Ticket</th>
                  <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Property / Unit</th>
                  <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Issue</th>
                  <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Status</th>
                  <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Urgency</th>
                  <th className="text-left text-xs font-medium text-gray-500 px-4 py-3">Vendor</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {requests.map(req => (
                  <tr key={req.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-5 py-3">
                      <Link to={`/requests/${req.id}`} className="text-xs font-mono text-teal-700 hover:underline">
                        {req.ticket_id}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-sm text-gray-900">{req.property_name}</p>
                      <p className="text-xs text-gray-400">Unit {req.unit}</p>
                    </td>
                    <td className="px-4 py-3 max-w-[200px]">
                      <p className="text-sm text-gray-700 truncate">{req.original_issue}</p>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={req.status} />
                    </td>
                    <td className="px-4 py-3">
                      {req.maintenance_pipeline_results?.urgency ? (
                        <UrgencyBadge level={req.maintenance_pipeline_results.urgency} />
                      ) : (
                        <span className="text-xs text-gray-300">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-gray-600">
                        {req.maintenance_pipeline_results?.assigned_vendor ?? '—'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
