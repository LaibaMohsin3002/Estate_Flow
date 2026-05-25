import { useState, FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Building, Eye, EyeOff, AlertCircle, MessageCircle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { supabase } from '../lib/supabase';

type AuthRole = 'tenant' | 'manager' | 'inspector' | 'admin' | 'vendor';

export default function Login() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: Location })?.from?.pathname ?? '/';

  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState<AuthRole>('tenant');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isSignUp, setIsSignUp] = useState(false);
  const [city, setCity] = useState('');
  const [area, setArea] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [locationStatus, setLocationStatus] = useState('');
  const [isLocating, setIsLocating] = useState(false);
  const [specialties, setSpecialties] = useState<string[]>([]);

  const isVendor = role === 'vendor';
  const vendorSpecialtyOptions = ['Plumbing', 'Electrical', 'HVAC', 'Painting', 'Carpentry', 'Cleaning', 'General'];

  function toggleSpecialty(specialty: string) {
    setSpecialties((current) =>
      current.includes(specialty)
        ? current.filter((item) => item !== specialty)
        : [...current, specialty]
    );
  }

  async function handleUseCurrentLocation() {
    if (!('geolocation' in navigator)) {
      setError('Geolocation is not supported in this browser.');
      return;
    }

    setError('');
    setLocationStatus('Detecting your current location…');
    setIsLocating(true);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLatitude(String(position.coords.latitude));
        setLongitude(String(position.coords.longitude));
        setLocationStatus('Location captured. Please add your city and area, then continue.');
        setIsLocating(false);
      },
      (geoError) => {
        setIsLocating(false);
        setLocationStatus('');
        setError(geoError.message || 'Unable to access your current location.');
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  async function handleSignIn(e: FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await signIn(email.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid credentials. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  async function handleSignUp(e: FormEvent) {
    e.preventDefault();
    const normalizedEmail = email.trim().toLowerCase();

    if (!fullName.trim()) { setError('Full name is required.'); return; }
    if (!normalizedEmail) { setError('Email address is required.'); return; }
    if (isVendor && !phone.trim()) { setError('WhatsApp number is required for vendors.'); return; }

    if (isVendor) {
      if (!city.trim()) { setError('City is required for vendors.'); return; }
      if (!area.trim()) { setError('Area is required for vendors.'); return; }
      if (!specialties.length) { setError('Select at least one specialty for vendors.'); return; }

      const parsedLat = Number(latitude);
      const parsedLon = Number(longitude);
      if (!Number.isFinite(parsedLat) || !Number.isFinite(parsedLon)) {
        setError('Please use current location to capture latitude and longitude.');
        return;
      }
    }

    setError('');
    setLoading(true);
    try {
      const { error: signUpErr } = await supabase.auth.signUp({
        email: normalizedEmail,
        password,
        options: {
          data: {
            full_name: fullName,
            role,
            phone: isVendor ? phone.trim() : undefined,
            city: isVendor ? city.trim() : undefined,
            area: isVendor ? area.trim() : undefined,
            latitude: isVendor ? Number(latitude) : undefined,
            longitude: isVendor ? Number(longitude) : undefined,
            specialties: isVendor ? specialties : undefined,
          },
          emailRedirectTo: `${globalThis.location.origin}/`,
        },
      });
      if (signUpErr) throw signUpErr;

      setError('');
      setEmail('');
      setPhone('');
      setPassword('');
      setFullName('');
      setCity('');
      setArea('');
      setLatitude('');
      setLongitude('');
      setLocationStatus('');
      setSpecialties([]);
      setIsSignUp(false);
      alert('Sign-up successful! Please sign in with your credentials.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign-up failed. Please try again.');
      console.error('Supabase signup failed', err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 bg-teal-700 rounded-xl flex items-center justify-center mb-4 shadow-card-md">
            <Building size={24} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">EstateFlow</h1>
          <p className="text-sm text-gray-500 mt-1">AI-powered property management</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-xl shadow-card-md border border-gray-100 p-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-1">
            {isSignUp ? 'Create account' : 'Sign in'}
          </h2>
          <p className="text-sm text-gray-500 mb-6">
            {isSignUp ? 'Join EstateFlow to manage properties' : 'Enter your credentials to continue'}
          </p>

          {error && (
            <div className="flex items-start gap-2.5 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5 mb-5">
              <AlertCircle size={16} className="text-red-500 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <form onSubmit={isSignUp ? handleSignUp : handleSignIn} className="space-y-4">
            {isSignUp && (
              <div>
                <label htmlFor="fullName" className="block text-sm font-medium text-gray-700 mb-1.5">
                  Full name
                </label>
                <input
                  id="fullName"
                  type="text"
                  autoComplete="name"
                  required={isSignUp}
                  value={fullName}
                  onChange={e => setFullName(e.target.value)}
                  placeholder="Your full name"
                  className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 transition-all placeholder-gray-400"
                />
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1.5">
                Email address
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 transition-all placeholder-gray-400"
              />
            </div>

            {isSignUp && isVendor && (
              <div>
                <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-1.5">
                  <span className="flex items-center gap-1.5">
                    <MessageCircle size={13} className="text-green-600" />
                    WhatsApp Number
                  </span>
                </label>
                <input
                  id="phone"
                  type="tel"
                  autoComplete="tel"
                  required={isSignUp}
                  value={phone}
                  onChange={e => setPhone(e.target.value)}
                  placeholder="03001234567 or +923001234567"
                  className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 transition-all placeholder-gray-400"
                />
                <p className="text-xs text-gray-400 mt-1">Used to send and receive vendor WhatsApp updates.</p>
              </div>
            )}

            {isSignUp && isVendor && (
              <div className="space-y-3 rounded-lg border border-gray-200 bg-gray-50 px-3 py-3">
                <div>
                  <label htmlFor="city" className="block text-sm font-medium text-gray-700 mb-1.5">
                    City
                  </label>
                  <input
                    id="city"
                    type="text"
                    value={city}
                    onChange={e => setCity(e.target.value)}
                    placeholder="Karachi"
                    className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 transition-all placeholder-gray-400"
                  />
                </div>

                <div>
                  <label htmlFor="area" className="block text-sm font-medium text-gray-700 mb-1.5">
                    Area
                  </label>
                  <input
                    id="area"
                    type="text"
                    value={area}
                    onChange={e => setArea(e.target.value)}
                    placeholder="Gulshan, DHA, etc."
                    className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 transition-all placeholder-gray-400"
                  />
                </div>

                <fieldset className="space-y-2">
                  <legend className="block text-sm font-medium text-gray-700 mb-1.5">
                    Specialty(s)
                  </legend>
                  <div className="grid grid-cols-2 gap-2">
                    {vendorSpecialtyOptions.map((specialty) => {
                      const selected = specialties.includes(specialty);
                      return (
                        <button
                          key={specialty}
                          type="button"
                          onClick={() => toggleSpecialty(specialty)}
                          className={`rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                            selected
                              ? 'border-teal-700 bg-teal-700 text-white'
                              : 'border-gray-200 bg-white text-gray-700 hover:border-teal-300'
                          }`}
                        >
                          {specialty}
                        </button>
                      );
                    })}
                  </div>
                </fieldset>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="latitude" className="block text-sm font-medium text-gray-700 mb-1.5">
                      Latitude
                    </label>
                    <input
                      id="latitude"
                      type="number"
                      step="0.000001"
                      value={latitude}
                      onChange={e => setLatitude(e.target.value)}
                      placeholder="24.8607"
                      className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 transition-all placeholder-gray-400"
                    />
                  </div>

                  <div>
                    <label htmlFor="longitude" className="block text-sm font-medium text-gray-700 mb-1.5">
                      Longitude
                    </label>
                    <input
                      id="longitude"
                      type="number"
                      step="0.000001"
                      value={longitude}
                      onChange={e => setLongitude(e.target.value)}
                      placeholder="67.0011"
                      className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 transition-all placeholder-gray-400"
                    />
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleUseCurrentLocation}
                  disabled={isLocating}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-lg border border-teal-600 text-teal-700 bg-white px-3 py-2 text-sm font-medium disabled:opacity-60"
                >
                  {isLocating ? 'Detecting…' : 'Use my current location'}
                </button>

                {locationStatus && (
                  <p className="text-xs text-gray-500">{locationStatus}</p>
                )}
              </div>
            )}

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete={isSignUp ? 'new-password' : 'current-password'}
                  required
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-3 py-2.5 pr-10 text-sm border border-gray-200 rounded-lg outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 transition-all placeholder-gray-400"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {isSignUp && (
              <div>
                <label htmlFor="role" className="block text-sm font-medium text-gray-700 mb-1.5">
                  I am a…
                </label>
                <select
                  id="role"
                  value={role}
                  onChange={e => setRole(e.target.value as AuthRole)}
                  className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 transition-all bg-white"
                >
                  <option value="tenant">Tenant</option>
                  <option value="manager">Property Manager</option>
                  <option value="inspector">Inspector</option>
                  <option value="admin">Administrator</option>
                  <option value="vendor">Vendor (email + WhatsApp)</option>
                </select>
              </div>
            )}

            {!isSignUp && (
              <div>
                <label htmlFor="signInRole" className="block text-sm font-medium text-gray-700 mb-1.5">
                  Signing in as…
                </label>
                <select
                  id="signInRole"
                  value={role}
                  onChange={e => setRole(e.target.value as AuthRole)}
                  className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 transition-all bg-white"
                >
                  <option value="tenant">Tenant</option>
                  <option value="manager">Property Manager</option>
                  <option value="inspector">Inspector</option>
                  <option value="admin">Administrator</option>
                  <option value="vendor">Vendor (email + WhatsApp)</option>
                </select>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-teal-700 hover:bg-teal-800 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium py-2.5 px-4 rounded-lg transition-colors text-sm flex items-center justify-center gap-2"
            >
              {loading && <div className="w-4 h-4 border-2 border-white/50 border-t-white rounded-full animate-spin" />}
              {loading ? (isSignUp ? 'Creating account…' : 'Signing in…') : (isSignUp ? 'Create account' : 'Sign in')}
            </button>
          </form>

          <p className="text-center text-sm text-gray-500 mt-6">
            {isSignUp ? 'Already have an account? ' : "Don't have an account? "}
            <button
              type="button"
              onClick={() => { setIsSignUp(!isSignUp); setError(''); }}
              className="text-teal-700 hover:text-teal-800 font-medium transition-colors"
            >
              {isSignUp ? 'Sign in' : 'Create one'}
            </button>
          </p>
        </div>

        <p className="text-center text-xs text-gray-400 mt-6">
          EstateFlow &copy; {new Date().getFullYear()} — Pakistan
        </p>
      </div>
    </div>
  );
}
