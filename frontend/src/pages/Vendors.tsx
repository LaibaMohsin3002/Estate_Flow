import { useEffect, useState } from 'react';
import { Users2, Star, Briefcase, MapPin, Phone, Mail, AlertCircle } from 'lucide-react';
import { fetchVendors } from '../services/estateflow';
import { Vendor } from '../types';
import { EmptyState } from '../components/EmptyState';
import { TableSkeleton } from '../components/LoadingSkeleton';

const SPECIALTY_COLORS: Record<string, string> = {
  Plumbing: 'bg-blue-50 text-blue-700 border-blue-200',
  Electrical: 'bg-amber-50 text-amber-700 border-amber-200',
  HVAC: 'bg-sky-50 text-sky-700 border-sky-200',
  Carpentry: 'bg-orange-50 text-orange-700 border-orange-200',
  Painting: 'bg-pink-50 text-pink-700 border-pink-200',
  General: 'bg-gray-100 text-gray-700 border-gray-200',
};

function StarRating({ rating }: { rating: number }) {
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map(i => (
        <Star
          key={i}
          size={12}
          className={i <= Math.round(rating) ? 'text-amber-400 fill-amber-400' : 'text-gray-200 fill-gray-200'}
        />
      ))}
      <span className="text-xs text-gray-500 ml-0.5">{rating.toFixed(1)}</span>
    </div>
  );
}

export default function Vendors() {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('');

  useEffect(() => {
    fetchVendors()
      .then(setVendors)
      .catch(() => setError('Could not load vendors.'))
      .finally(() => setLoading(false));
  }, []);

  const filtered = vendors.filter(v =>
    !filter ||
    v.name.toLowerCase().includes(filter.toLowerCase()) ||
    v.specialty.toLowerCase().includes(filter.toLowerCase()) ||
    v.city.toLowerCase().includes(filter.toLowerCase())
  );

  const specialties = [...new Set(vendors.map(v => v.specialty))];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Vendor Directory</h1>
        <p className="text-sm text-gray-500 mt-0.5">{vendors.length} registered vendors</p>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
          <AlertCircle size={15} className="text-red-500" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Specialty chips */}
      {!loading && specialties.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setFilter('')}
            className={`text-xs px-3 py-1 rounded-full border transition-colors font-medium ${!filter ? 'bg-teal-700 text-white border-teal-700' : 'bg-white text-gray-600 border-gray-200 hover:border-teal-300'}`}
          >
            All
          </button>
          {specialties.map(s => (
            <button
              key={s}
              onClick={() => setFilter(filter === s ? '' : s)}
              className={`text-xs px-3 py-1 rounded-full border transition-colors font-medium ${filter === s ? 'bg-teal-700 text-white border-teal-700' : 'bg-white text-gray-600 border-gray-200 hover:border-teal-300'}`}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Search */}
      <input
        type="search"
        placeholder="Search vendors by name, specialty, or city…"
        value={filter}
        onChange={e => setFilter(e.target.value)}
        className="w-full sm:max-w-sm px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 transition-all"
      />

      {loading ? (
        <div className="bg-white rounded-xl shadow-card border border-gray-100 p-5">
          <TableSkeleton rows={5} />
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<Users2 size={20} />}
          title="No vendors found"
          description={filter ? 'Try a different search term.' : 'No vendors registered yet.'}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(vendor => {
            const specialtyStyle = SPECIALTY_COLORS[vendor.specialty] ?? SPECIALTY_COLORS.General;
            return (
              <div key={vendor.id} className="bg-white rounded-xl shadow-card border border-gray-100 p-4 hover:shadow-card-md transition-shadow">
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div>
                    <p className="text-sm font-semibold text-gray-900">{vendor.name}</p>
                    <span className={`inline-block text-xs px-2 py-0.5 rounded-full border mt-1 font-medium ${specialtyStyle}`}>
                      {vendor.specialty}
                    </span>
                  </div>
                  <div className="w-9 h-9 rounded-lg bg-gray-50 border border-gray-100 flex items-center justify-center flex-shrink-0">
                    <Briefcase size={14} className="text-gray-400" />
                  </div>
                </div>

                <StarRating rating={vendor.rating} />

                <div className="mt-3 space-y-1.5">
                  <div className="flex items-center gap-1.5 text-xs text-gray-500">
                    <MapPin size={11} className="text-gray-400" />
                    {vendor.city}
                    {vendor.distance_km != null && (
                      <span className="ml-auto text-teal-600 font-medium">{vendor.distance_km.toFixed(1)} km</span>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-gray-500">
                    <Briefcase size={11} className="text-gray-400" />
                    {vendor.assignments} assignment{vendor.assignments !== 1 ? 's' : ''}
                  </div>
                  {vendor.phone && (
                    <div className="flex items-center gap-1.5 text-xs text-gray-500">
                      <Phone size={11} className="text-gray-400" />
                      {vendor.phone}
                    </div>
                  )}
                  {vendor.email && (
                    <div className="flex items-center gap-1.5 text-xs text-gray-500">
                      <Mail size={11} className="text-gray-400" />
                      <span className="truncate">{vendor.email}</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
