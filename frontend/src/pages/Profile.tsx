import { useEffect, useState } from 'react';
import {
  Briefcase,
  Mail,
  Phone,
  MapPin,
  Loader2,
  BellRing,
  CheckCircle2,
  AlertCircle,
  Building2,
} from 'lucide-react';
import { fetchProfile, updateProfile, fetchVendorActiveJobs, vendorReply } from '../services/estateflow';
import { useAuth } from '../contexts/AuthContext';
import { UserProfile } from '../types';

const VENDOR_SPECIALTIES = ['Plumbing', 'Electrical', 'HVAC', 'Painting', 'Carpentry', 'Cleaning', 'General'];

export default function Profile() {
  const { user, role } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [replyingId, setReplyingId] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [activeJobs, setActiveJobs] = useState<
    { id: string; ticket_id: string; original_issue: string; status: string; vendor_replied: boolean; created_at: string }[]
  >([]);
  const [form, setForm] = useState({
    full_name: '',
    phone: '',
    whatsapp_phone: '',
    area: '',
    city: '',
    latitude: '',
    longitude: '',
    specialties: [] as string[],
  });

  async function loadProfile() {
    setLoading(true);
    try {
      const res = await fetchProfile();
      setProfile(res);
      setForm({
        full_name: res.full_name ?? '',
        phone: res.phone ?? '',
        whatsapp_phone: res.whatsapp_phone ?? '',
        area: res.area ?? '',
        city: res.city ?? '',
        latitude: res.latitude != null ? String(res.latitude) : '',
        longitude: res.longitude != null ? String(res.longitude) : '',
        specialties: res.specialties?.length ? res.specialties : [],
      });
    } catch {
      setError('Could not load profile.');
    } finally {
      setLoading(false);
    }
  }

  async function loadJobs() {
    if (role !== 'vendor') return;
    setJobsLoading(true);
    try {
      setActiveJobs(await fetchVendorActiveJobs());
    } catch {
      setActiveJobs([]);
    } finally {
      setJobsLoading(false);
    }
  }

  useEffect(() => {
    loadProfile();
  }, []);

  useEffect(() => {
    loadJobs();
  }, [role]);

  async function handleSave(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      const updated = await updateProfile({
        full_name: form.full_name || undefined,
        phone: form.phone || undefined,
        whatsapp_phone: form.whatsapp_phone || undefined,
        area: form.area || undefined,
        city: form.city || undefined,
        latitude: form.latitude ? Number(form.latitude) : undefined,
        longitude: form.longitude ? Number(form.longitude) : undefined,
        specialties: form.specialties.length ? form.specialties : undefined,
      });
      setProfile(updated);
      setSuccess('Profile updated successfully.');
      await loadJobs();
    } catch {
      setError('Unable to save your profile right now.');
    } finally {
      setSaving(false);
    }
  }

  async function handleVendorReply(jobId: string) {
    setReplyingId(jobId);
    setError('');
    setSuccess('');
    try {
      await vendorReply(jobId);
      await loadJobs();
      setSuccess('Reminder sent via WhatsApp.');
    } catch {
      setError('Unable to send the reminder.');
    } finally {
      setReplyingId(null);
    }
  }

  function toggleSpecialty(specialty: string) {
    setForm((current) => ({
      ...current,
      specialties: current.specialties.includes(specialty)
        ? current.specialties.filter((item) => item !== specialty)
        : [...current.specialties, specialty],
    }));
  }

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto">
        <div className="animate-pulse bg-white rounded-xl border border-gray-100 p-6 space-y-4">
          <div className="h-5 w-28 bg-gray-200 rounded" />
          <div className="h-4 w-full bg-gray-200 rounded" />
          <div className="h-4 w-2/3 bg-gray-200 rounded" />
        </div>
      </div>
    );
  }

  const isVendor = role === 'vendor';

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <p className="text-sm text-teal-700 font-semibold">Profile</p>
        <h1 className="text-xl font-bold text-gray-900 mt-1">Manage your account</h1>
        <p className="text-sm text-gray-500 mt-1">
          {isVendor
            ? 'Update your vendor profile, service area, and WhatsApp details.'
            : 'Update your contact details and save your preferred WhatsApp number for notifications.'}
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-xl px-4 py-3">
          <AlertCircle size={16} className="text-red-500" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {success && (
        <div className="flex items-center gap-2 bg-green-50 border border-green-200 rounded-xl px-4 py-3">
          <CheckCircle2 size={16} className="text-green-600" />
          <p className="text-sm text-green-700">{success}</p>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-100 shadow-card p-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-12 h-12 rounded-xl bg-teal-50 flex items-center justify-center text-teal-700">
            <Briefcase size={18} />
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-900">{profile?.full_name || user?.email}</p>
            <p className="text-xs text-gray-500 capitalize">{role} account</p>
          </div>
        </div>

        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="text-sm font-medium text-gray-700">Full name</label>
            <input
              value={form.full_name}
              onChange={(e) => setForm((current) => ({ ...current, full_name: e.target.value }))}
              className="mt-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
              placeholder="Your name"
            />
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700">Mobile number</label>
              <div className="mt-1 flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-lg bg-gray-50">
                <Phone size={15} className="text-gray-400" />
                <input
                  value={form.phone}
                  onChange={(e) => setForm((current) => ({ ...current, phone: e.target.value }))}
                  className="w-full bg-transparent outline-none text-sm"
                  placeholder="Optional"
                />
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700">WhatsApp number</label>
              <div className="mt-1 flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-lg bg-gray-50">
                <BellRing size={15} className="text-gray-400" />
                <input
                  value={form.whatsapp_phone}
                  onChange={(e) => setForm((current) => ({ ...current, whatsapp_phone: e.target.value }))}
                  className="w-full bg-transparent outline-none text-sm"
                  placeholder="e.g. +923001234567"
                />
              </div>
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700">Email</label>
              <div className="mt-1 flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-lg bg-gray-50 text-sm text-gray-500">
                <Mail size={15} className="text-gray-400" />
                {profile?.email || user?.email || 'Not available'}
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Role</label>
              <div className="mt-1 px-3 py-2 border border-gray-200 rounded-lg bg-gray-50 text-sm text-gray-600 capitalize">
                {role}
              </div>
            </div>
          </div>

          {isVendor && (
            <>
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-700">Area</label>
                  <div className="mt-1 flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-lg bg-gray-50">
                    <MapPin size={15} className="text-gray-400" />
                    <input
                      value={form.area}
                      onChange={(e) => setForm((current) => ({ ...current, area: e.target.value }))}
                      className="w-full bg-transparent outline-none text-sm"
                      placeholder="Downtown"
                    />
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">City</label>
                  <input
                    value={form.city}
                    onChange={(e) => setForm((current) => ({ ...current, city: e.target.value }))}
                    className="mt-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
                    placeholder="Karachi"
                  />
                </div>
              </div>

              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-700">Latitude</label>
                  <input
                    type="number"
                    step="0.000001"
                    value={form.latitude}
                    onChange={(e) => setForm((current) => ({ ...current, latitude: e.target.value }))}
                    className="mt-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
                    placeholder="24.8607"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">Longitude</label>
                  <input
                    type="number"
                    step="0.000001"
                    value={form.longitude}
                    onChange={(e) => setForm((current) => ({ ...current, longitude: e.target.value }))}
                    className="mt-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
                    placeholder="67.0011"
                  />
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700">Specialties</label>
                <div className="mt-2 flex flex-wrap gap-2">
                  {VENDOR_SPECIALTIES.map((specialty) => {
                    const selected = form.specialties.includes(specialty);
                    return (
                      <button
                        key={specialty}
                        type="button"
                        onClick={() => toggleSpecialty(specialty)}
                        className={`px-3 py-1.5 rounded-full text-sm border transition-colors ${
                          selected
                            ? 'bg-teal-700 text-white border-teal-700'
                            : 'bg-white text-gray-700 border-gray-200 hover:border-teal-300'
                        }`}
                      >
                        {specialty}
                      </button>
                    );
                  })}
                </div>
              </div>
            </>
          )}

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 bg-teal-700 hover:bg-teal-800 disabled:opacity-60 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
            >
              {saving ? <Loader2 size={15} className="animate-spin" /> : <CheckCircle2 size={15} />}
              {saving ? 'Saving…' : 'Save profile'}
            </button>
          </div>
        </form>
      </div>

      {isVendor && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-sm font-semibold text-gray-900">Active jobs</p>
              <p className="text-xs text-gray-500">Accept or confirm your pending assignments via WhatsApp.</p>
            </div>
            <button
              type="button"
              onClick={() => loadJobs()}
              className="text-sm text-teal-700 font-medium"
            >
              Refresh
            </button>
          </div>

          {jobsLoading ? (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Loader2 size={14} className="animate-spin" />
              Loading active jobs…
            </div>
          ) : activeJobs.length === 0 ? (
            <div className="rounded-xl border border-dashed border-gray-200 px-4 py-5 text-sm text-gray-500">
              No active assignments right now.
            </div>
          ) : (
            <div className="space-y-3">
              {activeJobs.map((job) => (
                <div key={job.id} className="border border-gray-100 rounded-xl p-4 flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-mono text-gray-400">{job.ticket_id}</p>
                    <p className="text-sm font-medium text-gray-900 mt-1">{job.original_issue}</p>
                    <div className="mt-2 flex items-center gap-2">
                      <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium bg-gray-100 text-gray-700">
                        {job.status}
                      </span>
                      {job.vendor_replied ? (
                        <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium bg-green-100 text-green-700">
                          Reply sent
                        </span>
                      ) : (
                        <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium bg-amber-100 text-amber-700">
                          Awaiting reply
                        </span>
                      )}
                    </div>
                  </div>
                  <button
                    type="button"
                    disabled={replyingId === job.id || job.vendor_replied}
                    onClick={() => handleVendorReply(job.id)}
                    className="inline-flex items-center gap-2 bg-teal-700 hover:bg-teal-800 disabled:opacity-60 text-white text-sm font-medium px-3 py-2 rounded-lg transition-colors"
                  >
                    {replyingId === job.id ? <Loader2 size={14} className="animate-spin" /> : <Building2 size={14} />}
                    {job.vendor_replied ? 'Confirmed' : 'Send reminder'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
