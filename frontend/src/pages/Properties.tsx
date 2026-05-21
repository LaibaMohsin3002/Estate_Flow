import { useEffect, useState, FormEvent } from 'react';
import { Building2, Plus, X, MapPin, ChevronDown, ChevronRight, AlertCircle } from 'lucide-react';
import { createProperty, fetchProperties } from '../services/estateflow';
import { Property } from '../types';
import { useAuth } from '../contexts/AuthContext';
import { EmptyState } from '../components/EmptyState';
import { TableSkeleton } from '../components/LoadingSkeleton';

const canEdit = (role: string) => role === 'manager' || role === 'admin';

export default function Properties() {
  const { role } = useAuth();
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [error, setError] = useState('');

  // Form state
  const [name, setName] = useState('');
  const [city, setCity] = useState('');
  const [address, setAddress] = useState('');
  const [unitsInput, setUnitsInput] = useState('');
  const [lat, setLat] = useState('');
  const [lng, setLng] = useState('');
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    try {
      setProperties(await fetchProperties());
    } catch {
      setError('Could not load properties.');
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!name || !city || !address) { setFormError('Name, city, and address are required.'); return; }
    setFormError('');
    setSaving(true);
    try {
      const unit_numbers = unitsInput.split(',').map(s => s.trim()).filter(Boolean);
      await createProperty({
        name,
        city,
        address,
        unit_numbers,
        latitude: lat ? parseFloat(lat) : undefined,
        longitude: lng ? parseFloat(lng) : undefined,
      });
      setName(''); setCity(''); setAddress(''); setUnitsInput(''); setLat(''); setLng('');
      setShowForm(false);
      await load();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to save property.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Properties</h1>
          <p className="text-sm text-gray-500 mt-0.5">{properties.length} propert{properties.length === 1 ? 'y' : 'ies'}</p>
        </div>
        {canEdit(role) && (
          <button
            onClick={() => setShowForm(v => !v)}
            className="flex items-center gap-2 bg-teal-700 hover:bg-teal-800 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            {showForm ? <X size={15} /> : <Plus size={15} />}
            {showForm ? 'Cancel' : 'Add Property'}
          </button>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
          <AlertCircle size={15} className="text-red-500" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Add form */}
      {showForm && (
        <div className="bg-white rounded-xl shadow-card border border-gray-100 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">New Property</h2>
          {formError && (
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2 mb-4">
              <AlertCircle size={14} className="text-red-500" />
              <p className="text-xs text-red-700">{formError}</p>
            </div>
          )}
          <form onSubmit={handleCreate} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Name *</label>
              <input value={name} onChange={e => setName(e.target.value)} placeholder="Gulshan Residency" className="input" required />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">City *</label>
              <input value={city} onChange={e => setCity(e.target.value)} placeholder="Karachi" className="input" required />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Address *</label>
              <input value={address} onChange={e => setAddress(e.target.value)} placeholder="Block 5, Gulshan-e-Iqbal" className="input" required />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Units (comma-separated)</label>
              <input value={unitsInput} onChange={e => setUnitsInput(e.target.value)} placeholder="A1, A2, B1, B2, Ground Floor" className="input" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Latitude (optional)</label>
              <input type="number" step="any" value={lat} onChange={e => setLat(e.target.value)} placeholder="24.8607" className="input" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Longitude (optional)</label>
              <input type="number" step="any" value={lng} onChange={e => setLng(e.target.value)} placeholder="67.0104" className="input" />
            </div>
            <div className="sm:col-span-2 flex justify-end">
              <button
                type="submit"
                disabled={saving}
                className="flex items-center gap-2 bg-teal-700 hover:bg-teal-800 disabled:opacity-60 text-white text-sm font-medium px-5 py-2 rounded-lg transition-colors"
              >
                {saving && <div className="w-3.5 h-3.5 border border-white/50 border-t-white rounded-full animate-spin" />}
                {saving ? 'Saving…' : 'Save Property'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* List */}
      <div className="bg-white rounded-xl shadow-card border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="p-5"><TableSkeleton rows={4} /></div>
        ) : properties.length === 0 ? (
          <EmptyState
            icon={<Building2 size={20} />}
            title="No properties"
            description="Add your first property to get started."
          />
        ) : (
          <div className="divide-y divide-gray-50">
            {properties.map(prop => (
              <div key={prop.id}>
                <button
                  onClick={() => setExpandedId(expandedId === prop.id ? null : prop.id)}
                  className="w-full flex items-center gap-4 px-5 py-4 hover:bg-gray-50 transition-colors text-left"
                >
                  <div className="w-9 h-9 rounded-lg bg-teal-50 flex items-center justify-center flex-shrink-0">
                    <Building2 size={16} className="text-teal-700" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-900">{prop.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{prop.address} · {prop.city}</p>
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0">
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                      {prop.units?.length ?? 0} units
                    </span>
                    {expandedId === prop.id ? <ChevronDown size={15} className="text-gray-400" /> : <ChevronRight size={15} className="text-gray-400" />}
                  </div>
                </button>

                {expandedId === prop.id && (
                  <div className="px-5 pb-4 bg-gray-50/50 border-t border-gray-100">
                    <div className="pt-3 space-y-2">
                      {prop.lat != null && prop.lng != null && (
                        <div className="flex items-center gap-1.5 text-xs text-gray-500">
                          <MapPin size={12} className="text-gray-400" />
                          {prop.lat.toFixed(5)}, {prop.lng.toFixed(5)}
                        </div>
                      )}
                      {prop.units && prop.units.length > 0 && (
                        <div>
                          <p className="text-xs font-medium text-gray-500 mb-1.5">Units</p>
                          <div className="flex flex-wrap gap-1.5">
                            {prop.units.map(u => (
                              <span key={u} className="text-xs bg-white border border-gray-200 text-gray-700 px-2 py-0.5 rounded-md">
                                {u}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
