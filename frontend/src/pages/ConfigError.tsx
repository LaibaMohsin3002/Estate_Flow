import { Building, AlertTriangle } from 'lucide-react';

export default function ConfigError() {
  return (
    <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center px-4">
      <div className="w-full max-w-md text-center">
        <div className="w-14 h-14 bg-amber-100 rounded-xl flex items-center justify-center mx-auto mb-5">
          <AlertTriangle size={28} className="text-amber-600" />
        </div>

        <div className="flex items-center justify-center gap-2 mb-3">
          <Building size={18} className="text-teal-700" />
          <h1 className="text-lg font-bold text-gray-900">EstateFlow</h1>
        </div>

        <h2 className="text-base font-semibold text-gray-900 mb-2">Configuration Required</h2>
        <p className="text-sm text-gray-500 mb-6">
          Supabase environment variables are missing. Set the following variables to continue:
        </p>

        <div className="bg-gray-900 rounded-xl p-5 text-left mb-6 space-y-2">
          {['VITE_SUPABASE_URL', 'VITE_SUPABASE_ANON_KEY', 'VITE_API_URL'].map(key => (
            <div key={key} className="flex items-center gap-2">
              <span className="text-gray-500 text-xs font-mono">$</span>
              <span className="text-green-400 text-xs font-mono">{key}</span>
              <span className="text-gray-500 text-xs font-mono">=</span>
              <span className="text-amber-300 text-xs font-mono">your_value_here</span>
            </div>
          ))}
        </div>

        <p className="text-xs text-gray-400">
          Add these to your <code className="font-mono bg-gray-100 px-1 py-0.5 rounded">.env</code> file and restart the dev server.
        </p>
      </div>
    </div>
  );
}
