import { useEffect, useState, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { CalendarDays, CheckCircle2, AlertCircle, Loader2, ExternalLink } from 'lucide-react';
import { completeCalendarConnect, fetchCalendarStatus, getCalendarConnectUrl } from '../services/estateflow';

interface CalendarStatus {
  connected: boolean;
  provider: string;
  calendar_id: string;
  connected_at?: string;
}

export default function CalendarPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [status, setStatus] = useState<CalendarStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [message, setMessage] = useState('');
  const processingCodeRef = useRef<string | null>(null);

  async function loadStatus() {
    setLoading(true);
    try {
      const data = await fetchCalendarStatus();
      setStatus(data);
    } catch {
      setStatus({ connected: false, provider: 'google', calendar_id: 'primary' });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadStatus();
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const code = params.get('code');
    if (!code) return;

    if (processingCodeRef.current === code) return;
    processingCodeRef.current = code;

    async function finishConnect(authCode: string) {
      setConnecting(true);
      setMessage('');
      try {
        await completeCalendarConnect(authCode);
        setMessage('Google Calendar connected successfully.');
        await loadStatus();
      } catch {
        setMessage('Unable to connect Google Calendar. Please try again.');
      } finally {
        setConnecting(false);
        navigate('/calendar', { replace: true });
      }
    }

    void finishConnect(code);
  }, [location.search, navigate]);

  async function handleConnect() {
    setConnecting(true);
    setMessage('');
    try {
      const { auth_url } = await getCalendarConnectUrl();
      window.location.href = auth_url;
    } catch {
      setMessage('Unable to start Google Calendar authorization.');
      setConnecting(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <p className="text-sm text-teal-700 font-semibold">Calendar</p>
        <h1 className="text-xl font-bold text-gray-900 mt-1">Connect your Google Calendar</h1>
        <p className="text-sm text-gray-500 mt-1">
          Sync your own Google Calendar so scheduled maintenance visits can be added automatically.
        </p>
      </div>

      {message && (
        <div className={`flex items-center gap-2 rounded-xl border px-4 py-3 ${message.includes('success') ? 'bg-green-50 border-green-200 text-green-700' : 'bg-red-50 border-red-200 text-red-700'}`}>
          {message.includes('success') ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          <p className="text-sm">{message}</p>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-100 shadow-card p-6">
        <div className="flex items-start gap-3">
          <div className="w-12 h-12 rounded-xl bg-teal-50 flex items-center justify-center text-teal-700">
            <CalendarDays size={18} />
          </div>
          <div className="flex-1">
            <p className="text-sm font-semibold text-gray-900">Current connection</p>
            {loading ? (
              <div className="flex items-center gap-2 text-sm text-gray-500 mt-2">
                <Loader2 size={14} className="animate-spin" />
                Loading calendar status…
              </div>
            ) : status?.connected ? (
              <div className="mt-2 space-y-1 text-sm text-gray-600">
                <p>Connected to <span className="font-semibold text-gray-900">{status.provider}</span>.</p>
                <p>Calendar: <span className="font-semibold text-gray-900">{status.calendar_id}</span></p>
                {status.connected_at && <p>Connected on {new Date(status.connected_at).toLocaleString()}</p>}
              </div>
            ) : (
              <p className="mt-2 text-sm text-gray-500">Google Calendar is not connected yet.</p>
            )}
          </div>
        </div>

        <div className="mt-5 flex items-center gap-3">
          <button
            type="button"
            onClick={handleConnect}
            disabled={connecting}
            className="inline-flex items-center gap-2 bg-teal-700 hover:bg-teal-800 disabled:opacity-60 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            {connecting ? <Loader2 size={15} className="animate-spin" /> : <ExternalLink size={15} />}
            {connecting ? 'Connecting…' : status?.connected ? 'Reconnect Google Calendar' : 'Connect Google Calendar'}
          </button>
          <button
            type="button"
            onClick={() => void loadStatus()}
            className="text-sm text-teal-700 font-medium"
          >
            Refresh
          </button>
        </div>
      </div>
    </div>
  );
}
