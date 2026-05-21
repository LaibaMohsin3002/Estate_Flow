import { useEffect, useState, FormEvent } from 'react';
import { ClipboardList, Plus, X, Calendar, AlertCircle, CheckCircle2, Clock } from 'lucide-react';
import {
  createInspection,
  fetchInspections,
  fetchProperties,
} from '../services/estateflow';
import { Inspection, Property } from '../types';
import { EmptyState } from '../components/EmptyState';
import { TableSkeleton } from '../components/LoadingSkeleton';
import { useAuth } from '../contexts/AuthContext';

const STATUS_STYLES: Record<Inspection['status'], string> = {
  Scheduled: 'bg-sky-50 text-sky-700 border-sky-200',
  'In Progress': 'bg-teal-50 text-teal-700 border-teal-200',
  Completed: 'bg-green-50 text-green-700 border-green-200',
  Cancelled: 'bg-gray-100 text-gray-500 border-gray-200',
};

export default function Inspections() {
  const { role } = useAuth();
  const [inspections, setInspections] = useState<Inspection[]>([]);
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState('');

  // Form
  const [propId, setPropId] = useState('');
  const [scheduledDate, setScheduledDate] = useState('');
  const [inspectorName, setInspectorName] = useState('');
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');

  useEffect(() => { loadAll(); }, []);

  async function loadAll() {
    setLoading(true);
    try {
      const [insp, props] = await Promise.all([
        fetchInspections().catch(() => [] as Inspection[]),
        fetchProperties().catch(() => [] as Property[]),
      ]);
      setInspections(insp);
      setProperties(props);
    } catch {
      setError('Could not load inspections.');
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!propId || !scheduledDate || !inspectorName) {
      setFormError('All fields are required.');
      return;
    }
    setFormError('');
    setSaving(true);
    try {
      const prop = properties.find((p) => p.id === propId);
      if (!prop) {
        setFormError('Property not found.');
        return;
      }
      await createInspection({
        property_id: propId,
        property_name: prop.name,
        inspection_type: 'Routine',
        items: [
          {
            item_name: 'General property walkthrough',
            result: 'pass',
            note: `Scheduled ${scheduledDate} — inspector ${inspectorName}`,
          },
        ],
        notes: { scheduled_date: scheduledDate, inspector_name: inspectorName },
      });
      setPropId(''); setScheduledDate(''); setInspectorName('');
      setShowForm(false);
      await loadAll();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to create inspection.');
    } finally {
      setSaving(false);
    }
  }

  const canCreate = role === 'manager' || role === 'admin' || role === 'inspector';

  const grouped = {
    upcoming: inspections.filter(i => i.status === 'Scheduled' || i.status === 'In Progress'),
    completed: inspections.filter(i => i.status === 'Completed'),
    cancelled: inspections.filter(i => i.status === 'Cancelled'),
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Inspections</h1>
          <p className="text-sm text-gray-500 mt-0.5">{inspections.length} total inspections</p>
        </div>
        {canCreate && (
          <button
            onClick={() => setShowForm(v => !v)}
            className="flex items-center gap-2 bg-teal-700 hover:bg-teal-800 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            {showForm ? <X size={15} /> : <Plus size={15} />}
            {showForm ? 'Cancel' : 'New Inspection'}
          </button>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
          <AlertCircle size={15} className="text-red-500" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Create form */}
      {showForm && (
        <div className="bg-white rounded-xl shadow-card border border-gray-100 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">Schedule Inspection</h2>
          {formError && (
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2 mb-4">
              <AlertCircle size={13} className="text-red-500" />
              <p className="text-xs text-red-700">{formError}</p>
            </div>
          )}
          <form onSubmit={handleCreate} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Property *</label>
              <select value={propId} onChange={e => setPropId(e.target.value)} className="input" required>
                <option value="">Select…</option>
                {properties.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Inspector Name *</label>
              <input value={inspectorName} onChange={e => setInspectorName(e.target.value)} placeholder="Bilal Ahmed" className="input" required />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Scheduled Date *</label>
              <input type="date" value={scheduledDate} onChange={e => setScheduledDate(e.target.value)} className="input" required />
            </div>
            <div className="sm:col-span-3 flex justify-end">
              <button
                type="submit"
                disabled={saving}
                className="flex items-center gap-2 bg-teal-700 hover:bg-teal-800 disabled:opacity-60 text-white text-sm font-medium px-5 py-2 rounded-lg transition-colors"
              >
                {saving && <div className="w-3.5 h-3.5 border border-white/50 border-t-white rounded-full animate-spin" />}
                {saving ? 'Scheduling…' : 'Schedule'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-xl shadow-card border border-gray-100 p-4 text-center">
          <Clock size={16} className="text-sky-500 mx-auto mb-1" />
          <p className="text-2xl font-bold text-gray-900">{grouped.upcoming.length}</p>
          <p className="text-xs text-gray-500">Upcoming</p>
        </div>
        <div className="bg-white rounded-xl shadow-card border border-gray-100 p-4 text-center">
          <CheckCircle2 size={16} className="text-green-500 mx-auto mb-1" />
          <p className="text-2xl font-bold text-gray-900">{grouped.completed.length}</p>
          <p className="text-xs text-gray-500">Completed</p>
        </div>
        <div className="bg-white rounded-xl shadow-card border border-gray-100 p-4 text-center">
          <ClipboardList size={16} className="text-gray-400 mx-auto mb-1" />
          <p className="text-2xl font-bold text-gray-900">{inspections.length}</p>
          <p className="text-xs text-gray-500">Total</p>
        </div>
      </div>

      {/* List */}
      <div className="bg-white rounded-xl shadow-card border border-gray-100 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="text-sm font-semibold text-gray-900">All Inspections</h2>
        </div>
        {loading ? (
          <div className="p-5"><TableSkeleton rows={4} /></div>
        ) : inspections.length === 0 ? (
          <EmptyState
            icon={<ClipboardList size={20} />}
            title="No inspections"
            description="Schedule an inspection to get started."
          />
        ) : (
          <div className="divide-y divide-gray-50">
            {inspections.map(insp => (
              <div key={insp.id} className="px-5 py-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Calendar size={14} className="text-gray-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <p className="text-sm font-semibold text-gray-900">{insp.property_name}</p>
                      <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${STATUS_STYLES[insp.status]}`}>
                        {insp.status}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500">
                      Inspector: {insp.inspector_name} · {new Date(insp.scheduled_date).toLocaleDateString()}
                    </p>
                    {insp.ai_summary && (
                      <p className="mt-2 text-xs text-gray-600 bg-teal-50 border border-teal-100 rounded-lg p-2.5">
                        <span className="font-medium text-teal-700">AI Summary: </span>{insp.ai_summary}
                      </p>
                    )}
                  </div>
                  {insp.risk_score != null && (
                    <div className="flex-shrink-0 text-right">
                      <p className={`text-sm font-bold ${insp.risk_score >= 0.7 ? 'text-red-600' : insp.risk_score >= 0.4 ? 'text-amber-600' : 'text-green-600'}`}>
                        {Math.round(insp.risk_score * 100)}%
                      </p>
                      <p className="text-xs text-gray-400">risk</p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
