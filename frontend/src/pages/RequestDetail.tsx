import { useEffect, useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import {
  ArrowLeft, Building2, Home, Calendar, FileText,
  PenSquare, CheckCircle2, Clock, AlertCircle
} from 'lucide-react';
import { fetchMaintenanceRequest } from '../services/estateflow';
import { MaintenanceRequest } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { UrgencyBadge } from '../components/UrgencyBadge';
import { AgentPipelineLive } from '../components/AgentPipelineLive';
import { Skeleton } from '../components/LoadingSkeleton';

export default function RequestDetail() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const live = searchParams.get('live') === '1';

  const [request, setRequest] = useState<MaintenanceRequest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    fetchMaintenanceRequest(id)
      .then(setRequest)
      .catch(() => setError('Could not load request.'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto space-y-4">
        <Skeleton className="h-6 w-40" />
        <div className="bg-white rounded-xl p-5 space-y-3 border border-gray-100">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      </div>
    );
  }

  if (error || !request) {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-xl px-5 py-4">
          <AlertCircle size={18} className="text-red-500" />
          <p className="text-sm text-red-700">{error || 'Request not found.'}</p>
        </div>
      </div>
    );
  }

  const pipeline = request.maintenance_pipeline_results;

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      {/* Back */}
      <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors">
        <ArrowLeft size={15} />
        Back to dashboard
      </Link>

      {/* Header card */}
      <div className="bg-white rounded-xl shadow-card border border-gray-100 p-5">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <div className="flex items-center gap-2 flex-wrap mb-2">
              <span className="text-xs font-mono bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{request.ticket_id}</span>
              <StatusBadge status={request.status} />
              {pipeline?.urgency && <UrgencyBadge level={pipeline.urgency} />}
            </div>
            <h1 className="text-lg font-bold text-gray-900">{request.original_issue}</h1>
          </div>
          <p className="text-xs text-gray-400 flex-shrink-0">
            {new Date(request.created_at).toLocaleString()}
          </p>
        </div>

        <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-3">
          <InfoItem icon={<Building2 size={14} />} label="Property" value={request.property_name} />
          <InfoItem icon={<Home size={14} />} label="Unit" value={request.unit} />
          <InfoItem icon={<Clock size={14} />} label="Tenant" value={request.tenant_name} />
          {pipeline?.category && <InfoItem icon={<FileText size={14} />} label="Category" value={pipeline.category} />}
          {pipeline?.sla_target_hours != null && (
            <InfoItem icon={<Clock size={14} />} label="SLA" value={`${pipeline.sla_target_hours}h`} />
          )}
          {pipeline?.scheduled_time && (
            <InfoItem icon={<Calendar size={14} />} label="Scheduled" value={new Date(pipeline.scheduled_time).toLocaleDateString()} />
          )}
          {pipeline?.assigned_vendor && (
            <InfoItem icon={<Building2 size={14} />} label="Vendor" value={pipeline.assigned_vendor} />
          )}
        </div>
      </div>

      {/* Live pipeline */}
      {id && <AgentPipelineLive requestId={id} live={live} />}

      {/* Report section */}
      {pipeline && (
        <div className="bg-white rounded-xl shadow-card border border-gray-100 p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
            <FileText size={15} className="text-gray-400" />
            Report
          </h2>

          {pipeline.report_summary && (
            <p className="text-sm text-gray-700 leading-relaxed">{pipeline.report_summary}</p>
          )}

          <div className="flex items-center gap-3">
            {pipeline.report_signed ? (
              <div className="flex items-center gap-2 text-green-600 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
                <CheckCircle2 size={15} />
                <span className="text-sm font-medium">Report signed</span>
              </div>
            ) : pipeline.report_pending_signature ? (
              <div className="flex items-center gap-2 text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                <PenSquare size={15} />
                <span className="text-sm font-medium">Draft — awaiting manager signature</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-gray-500 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
                <FileText size={15} />
                <span className="text-sm">Report not yet generated</span>
              </div>
            )}

            {(request.status === 'Pending Approval' || pipeline.report_pending_signature) && (
              <Link
                to="/approvals"
                className="text-sm text-teal-700 font-medium hover:underline ml-auto"
              >
                Go to Approvals →
              </Link>
            )}
          </div>

          {pipeline.recommended_model && (
            <p className="text-xs text-gray-400">Recommended model: {pipeline.recommended_model}</p>
          )}
        </div>
      )}
    </div>
  );
}

function InfoItem({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-start gap-2">
      <span className="text-gray-400 mt-0.5 flex-shrink-0">{icon}</span>
      <div>
        <p className="text-xs text-gray-400">{label}</p>
        <p className="text-sm font-medium text-gray-900">{value}</p>
      </div>
    </div>
  );
}
