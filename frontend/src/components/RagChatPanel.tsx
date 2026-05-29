import { useEffect, useRef, useState, FormEvent } from 'react';
import { MessageSquare, Send, Loader2, BookOpen } from 'lucide-react';
import { chatManager, chatTenant, fetchProperties } from '../services/estateflow';
import { ChatSource, Property } from '../types';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: ChatSource[];
}

interface RagChatPanelProps {
  mode: 'manager' | 'tenant';
  defaultPropertyId?: string;
}

export function RagChatPanel({ mode, defaultPropertyId }: RagChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [properties, setProperties] = useState<Property[]>([]);
  const [propertyId, setPropertyId] = useState(defaultPropertyId ?? '');
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (mode === 'manager') {
      fetchProperties()
        .then(setProperties)
        .catch(() => setProperties([]));
    }
  }, [mode]);

  useEffect(() => {
    if (defaultPropertyId) setPropertyId(defaultPropertyId);
  }, [defaultPropertyId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    setError('');
    setInput('');
    const userMsg: ChatMessage = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const res =
        mode === 'manager'
          ? await chatManager({
              message: text,
              history,
              property_id: propertyId || undefined,
            })
          : await chatTenant({ message: text, history });

      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: res.answer, sources: res.sources },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chat failed.');
    } finally {
      setLoading(false);
    }
  }

  const title = mode === 'manager' ? 'Property Assistant' : 'Maintenance Help';
  const subtitle =
    mode === 'manager'
      ? 'Ask about tickets, inspections, and policies for your buildings.'
      : 'Ask about your requests, status, and what to do next.';

  return (
    <div className="bg-white rounded-xl shadow-card border border-gray-100 flex flex-col h-[420px]">
      <div className="px-5 py-4 border-b border-gray-100 flex-shrink-0">
        <div className="flex items-center gap-2">
          <MessageSquare size={16} className="text-teal-700" />
          <h2 className="text-sm font-semibold text-gray-900">{title}</h2>
          <span className="text-[10px] bg-violet-50 text-violet-700 px-1.5 py-0.5 rounded border border-violet-100">
            RAG
          </span>
        </div>
        <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
        {mode === 'manager' && properties.length > 0 && (
          <select
            value={propertyId}
            onChange={(e) => setPropertyId(e.target.value)}
            className="mt-2 w-full text-xs border border-gray-200 rounded-lg px-2 py-1.5 outline-none focus:border-teal-500"
          >
            <option value="">All properties / global policies</option>
            {properties.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-0">
        {messages.length === 0 && !loading && (
          <div className="text-center py-8 text-gray-400 text-xs">
            <BookOpen size={28} className="mx-auto mb-2 opacity-40" />
            {mode === 'manager'
              ? 'Try: "What recurring plumbing issues do we have?"'
              : 'Try: "How do I check status of my maintenance request?"'}
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed ${
                m.role === 'user'
                  ? 'bg-teal-700 text-white'
                  : 'bg-gray-50 text-gray-800 border border-gray-100'
              }`}
            >
              <p className="whitespace-pre-wrap">{m.content}</p>
              {m.sources && m.sources.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-200/80">
                  <p className="text-[10px] font-semibold text-gray-500 mb-1">Sources</p>
                  <ul className="space-y-0.5">
                    {m.sources.slice(0, 3).map((s, j) => (
                      <li key={j} className="text-[10px] text-gray-500 truncate">
                        {s.title}: {s.snippet}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <Loader2 size={14} className="animate-spin" />
            Thinking…
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && (
        <p className="px-4 text-xs text-red-500 flex-shrink-0">{error}</p>
      )}

      <form onSubmit={handleSubmit} className="p-3 border-t border-gray-100 flex gap-2 flex-shrink-0">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your question…"
          className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-2 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="p-2 bg-teal-700 hover:bg-teal-800 disabled:opacity-50 text-white rounded-lg transition-colors"
          aria-label="Send"
        >
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}
