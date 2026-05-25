import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight, Clock, Loader2, AlertCircle } from 'lucide-react';
import { fetchMaintenanceRequests } from '../services/estateflow';
import { MaintenanceRequest } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { UrgencyBadge } from '../components/UrgencyBadge';
import { EmptyState } from '../components/EmptyState';

export default function UnderProcess() {
  const [requests, setRequests] = useState<MaintenanceRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let mounted = true;

    fetchMaintenanceRequests()
      .then((items) => {
        if (!mounted) return;
        setRequests(items.filter((item) => ['Open', 'In Progress'].includes(item.status)));
      })
      .catch(() => {
        if (!mounted) return;
        setError('Could not load active requests.');
      })
      .finally(() => {
        if (!mounted) return;
        setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm text-teal-700 font-semibold">Under Process</p>
        <h1 className="text-xl font-bold text-gray-900 mt-1">Active maintenance requests</h1>
        <p className="text-sm text-gray-500 mt-1">
          Track requests that are currently being reviewed, assigned, or worked on.
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-xl px-5 py-4">
          <AlertCircle size={18} className="text-red-500" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {loading ? (
        <div className="bg-white rounded-xl border border-gray-100 p-5">
          <div className="flex items-center gap-2 text-gray-500 text-sm">
            <Loader2 size={16} className="animate-spin" />
            Loading active requests…
          </div>
        </div>
      ) : requests.length === 0 ? (
        <EmptyState
          icon={<Clock size={20} />}
          title="No active requests"
          description="Your maintenance pipeline is currently idle. New requests will appear here as soon as they start processing."
        />
      ) : (
        <div className="bg-white rounded-xl shadow-card border border-gray-100 overflow-hidden">
          <div className="divide-y divide-gray-50">
            {requests.map((request) => (
              <Link
                key={request.id}
                to={`/requests/${request.id}?live=1`}
                className="flex items-center gap-4 px-5 py-4 hover:bg-gray-50 transition-colors group"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-mono text-gray-400">{request.ticket_id}</span>
                    <StatusBadge status={request.status} />
                    {request.maintenance_pipeline_results?.urgency && (
                      <UrgencyBadge level={request.maintenance_pipeline_results.urgency} />
                    )}
                  </div>
                  <p className="text-sm font-medium text-gray-900 mt-1 truncate">{request.original_issue}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {request.property_name} · Unit {request.unit}
                  </p>
                </div>
                <ChevronRight size={16} className="text-gray-300 group-hover:text-gray-400" />
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
