import { useState, useEffect, useRef, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera, X, AlertCircle, Locate, CheckCircle2 } from 'lucide-react';
import {
  fetchProperties,
  submitMaintenanceJson,
  submitMaintenanceWithMedia,
} from '../services/estateflow';
import { Property } from '../types';

interface GeoPosition {
  lat: number;
  lng: number;
  accuracy?: number;
}

export default function SubmitRequest() {
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);

  const [properties, setProperties] = useState<Property[]>([]);
  const [propertyId, setPropertyId] = useState('');
  const [unit, setUnit] = useState('');
  const [issue, setIssue] = useState('');
  const [photos, setPhotos] = useState<File[]>([]);
  const [photoPreviews, setPhotoPreviews] = useState<string[]>([]);
  const [geo, setGeo] = useState<GeoPosition | null>(null);
  const [geoLoading, setGeoLoading] = useState(false);
  const [geoError, setGeoError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const selectedProperty = properties.find(p => p.id === propertyId);
  const units = selectedProperty?.units ?? [];

  useEffect(() => {
    fetchProperties()
      .then(setProperties)
      .catch(() => setProperties([]));
  }, []);

  function captureGeo() {
    if (!navigator.geolocation) {
      setGeoError('Geolocation not supported by your browser.');
      return;
    }
    setGeoLoading(true);
    setGeoError('');
    navigator.geolocation.getCurrentPosition(
      pos => {
        setGeo({ lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: pos.coords.accuracy });
        setGeoLoading(false);
      },
      err => {
        setGeoError(err.message || 'Could not get location.');
        setGeoLoading(false);
      },
      { timeout: 10000 }
    );
  }

  function addPhotos(files: FileList | null) {
    if (!files) return;
    const newFiles = Array.from(files).slice(0, 5 - photos.length);
    const previews = newFiles.map(f => URL.createObjectURL(f));
    setPhotos(prev => [...prev, ...newFiles]);
    setPhotoPreviews(prev => [...prev, ...previews]);
  }

  function removePhoto(idx: number) {
    URL.revokeObjectURL(photoPreviews[idx]);
    setPhotos(prev => prev.filter((_, i) => i !== idx));
    setPhotoPreviews(prev => prev.filter((_, i) => i !== idx));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!propertyId || !unit || !issue.trim()) {
      setError('Please fill in all required fields.');
      return;
    }
    setError('');
    setSubmitting(true);

    try {
      if (!selectedProperty) {
        setError('Please select a property.');
        return;
      }

      let requestId: string;

      if (photos.length > 0) {
        const form = new FormData();
        form.append('property_id', propertyId);
        form.append('property_name', selectedProperty.name);
        form.append('unit', unit);
        form.append('original_issue', issue);
        if (geo) {
          form.append('latitude', String(geo.lat));
          form.append('longitude', String(geo.lng));
        }
        photos.forEach((f) => form.append('images', f));
        requestId = await submitMaintenanceWithMedia(form);
      } else {
        requestId = await submitMaintenanceJson({
          property_id: propertyId,
          property_name: selectedProperty.name,
          unit,
          original_issue: issue,
          latitude: geo?.lat,
          longitude: geo?.lng,
        });
      }

      navigate(`/requests/${requestId}?live=1`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Submission failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Submit Maintenance Request</h1>
        <p className="text-sm text-gray-500 mt-0.5">Describe the issue and our AI will classify and assign it automatically.</p>
      </div>

      {error && (
        <div className="flex items-start gap-2.5 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
          <AlertCircle size={16} className="text-red-500 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Property */}
        <div className="bg-white rounded-xl shadow-card border border-gray-100 p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-900">Location Details</h2>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5" htmlFor="property">
              Property <span className="text-red-500">*</span>
            </label>
            <select
              id="property"
              value={propertyId}
              onChange={e => { setPropertyId(e.target.value); setUnit(''); }}
              className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 transition-all bg-white"
              required
            >
              <option value="">Select property…</option>
              {properties.map(p => (
                <option key={p.id} value={p.id}>{p.name} — {p.city}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5" htmlFor="unit">
              Unit <span className="text-red-500">*</span>
            </label>
            {units.length > 0 ? (
              <select
                id="unit"
                value={unit}
                onChange={e => setUnit(e.target.value)}
                className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 transition-all bg-white"
                required
              >
                <option value="">Select unit…</option>
                {units.map(u => <option key={u} value={u}>{u}</option>)}
              </select>
            ) : (
              <input
                id="unit"
                type="text"
                value={unit}
                onChange={e => setUnit(e.target.value)}
                placeholder="e.g. 3A, Ground Floor"
                className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 transition-all"
                required
              />
            )}
          </div>
        </div>

        {/* Issue */}
        <div className="bg-white rounded-xl shadow-card border border-gray-100 p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-900">Issue Description</h2>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5" htmlFor="issue">
              Describe the problem <span className="text-red-500">*</span>
            </label>
            <textarea
              id="issue"
              value={issue}
              onChange={e => setIssue(e.target.value)}
              rows={5}
              placeholder="Describe the issue in detail (English, Urdu, or Roman Urdu)…"
              className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 transition-all resize-none"
              required
            />
            <p className="text-xs text-gray-400 mt-1">{issue.length} characters</p>
          </div>
        </div>

        {/* Photos */}
        <div className="bg-white rounded-xl shadow-card border border-gray-100 p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-900">Photos (optional)</h2>

          <div
            onClick={() => fileRef.current?.click()}
            className="border-2 border-dashed border-gray-200 rounded-lg p-6 flex flex-col items-center gap-2 cursor-pointer hover:border-teal-400 hover:bg-teal-50/30 transition-colors"
          >
            <Camera size={24} className="text-gray-300" />
            <p className="text-sm text-gray-500">Tap to add photos</p>
            <p className="text-xs text-gray-400">Up to 5 images (JPG, PNG)</p>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={e => addPhotos(e.target.files)}
          />

          {photoPreviews.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {photoPreviews.map((src, i) => (
                <div key={i} className="relative w-20 h-20 rounded-lg overflow-hidden border border-gray-200">
                  <img src={src} alt={`Photo ${i + 1}`} className="w-full h-full object-cover" />
                  <button
                    type="button"
                    onClick={() => removePhoto(i)}
                    className="absolute top-0.5 right-0.5 w-5 h-5 bg-black/60 rounded-full flex items-center justify-center"
                    aria-label="Remove photo"
                  >
                    <X size={10} className="text-white" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Geolocation */}
        <div className="bg-white rounded-xl shadow-card border border-gray-100 p-5 space-y-3">
          <h2 className="text-sm font-semibold text-gray-900">Location (optional)</h2>
          <p className="text-xs text-gray-500">Helps match the nearest available vendor.</p>

          {geo ? (
            <div className="flex items-center gap-2 bg-teal-50 border border-teal-100 rounded-lg px-3 py-2.5">
              <CheckCircle2 size={16} className="text-teal-600 flex-shrink-0" />
              <div>
                <p className="text-xs font-medium text-teal-800">Location captured</p>
                <p className="text-xs text-teal-600">{geo.lat.toFixed(5)}, {geo.lng.toFixed(5)}{geo.accuracy ? ` ±${Math.round(geo.accuracy)}m` : ''}</p>
              </div>
              <button type="button" onClick={() => setGeo(null)} className="ml-auto text-teal-500 hover:text-teal-700">
                <X size={14} />
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={captureGeo}
              disabled={geoLoading}
              className="flex items-center gap-2 text-sm text-teal-700 font-medium border border-teal-200 px-4 py-2 rounded-lg hover:bg-teal-50 disabled:opacity-50 transition-colors"
            >
              <Locate size={15} className={geoLoading ? 'animate-pulse' : ''} />
              {geoLoading ? 'Getting location…' : 'Use my location'}
            </button>
          )}

          {geoError && <p className="text-xs text-red-500">{geoError}</p>}
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full bg-teal-700 hover:bg-teal-800 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium py-3 px-6 rounded-lg transition-colors text-sm flex items-center justify-center gap-2"
        >
          {submitting && <div className="w-4 h-4 border-2 border-white/50 border-t-white rounded-full animate-spin" />}
          {submitting ? 'Submitting…' : 'Submit Request'}
        </button>
      </form>
    </div>
  );
}
