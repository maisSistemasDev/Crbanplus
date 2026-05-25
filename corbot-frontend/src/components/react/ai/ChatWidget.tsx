import { useState, useRef, useEffect } from 'react';
import { Bot, X, Send, Loader2, MessageSquare, ChevronDown } from 'lucide-react';
import { api } from '../../../lib/api/client';
import { ENDPOINTS } from '../../../lib/api/endpoints';
import { pendingTour } from '../../../lib/tour/store';
import { TOURS } from '../../../lib/tour/tours';
import type { AiConversation, AiMessage } from '../../../lib/api/types';

function Message({ msg }: { msg: AiMessage }) {
  const isUser = msg.role === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      {!isUser && (
        <div className="h-7 w-7 rounded-full bg-indigo-600 flex items-center justify-center mr-2 shrink-0 mt-0.5">
          <Bot size={14} className="text-white" />
        </div>
      )}
      <div
        className={`max-w-[80%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? 'bg-indigo-600 text-white rounded-tr-sm'
            : 'bg-gray-100 text-gray-800 rounded-tl-sm'
        }`}
      >
        {msg.content}
      </div>
    </div>
  );
}

export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<AiMessage[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (open) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
      inputRef.current?.focus();
    }
  }, [open, messages.length]);

  async function ensureConversation(): Promise<number> {
    if (conversationId) return conversationId;
    const res = await api.post<AiConversation>(ENDPOINTS.AI_CONVERSATIONS, {});
    setConversationId(res.id);
    return res.id;
  }

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: AiMessage = {
      id: Date.now(),
      role: 'user',
      content: text,
      tool_calls: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const convId = await ensureConversation();
      const res = await api.post<{ reply: string; tour_name: string | null; conversation_id: number }>(
        `${ENDPOINTS.AI_CONVERSATIONS}${convId}/message/`,
        { content: text },
      );

      const replyText = res.reply ?? '';

      // Dispara tour se a IA sugeriu
      if (res.tour_name) {
        const steps = TOURS[res.tour_name];
        if (steps) pendingTour.set(steps);
      }

      const assistantMsg: AiMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: replyText,
        tool_calls: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      const errMsg: AiMessage = {
        id: Date.now() + 2,
        role: 'assistant',
        content: 'Desculpe, ocorreu um erro. Tente novamente.',
        tool_calls: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const suggestions = [
    'Como criar uma equipe de comissão?',
    'Como aceitar uma sugestão de tabela?',
    'Como importar comissões por CSV?',
  ];

  return (
    <>
      {/* Botão flutuante */}
      <button
        onClick={() => setOpen((o) => !o)}
        data-tour="chat-widget-btn"
        aria-label="Abrir assistente"
        className="fixed bottom-6 right-6 z-50 h-14 w-14 rounded-full bg-indigo-600 text-white shadow-lg hover:bg-indigo-700 active:scale-95 transition-all flex items-center justify-center"
      >
        {open ? <ChevronDown size={22} /> : <MessageSquare size={22} />}
      </button>

      {/* Painel do chat */}
      {open && (
        <div
          className="fixed bottom-24 right-6 z-50 w-[360px] rounded-2xl bg-white shadow-2xl border border-gray-200 flex flex-col overflow-hidden"
          style={{ maxHeight: 'min(560px, calc(100vh - 120px))' }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 bg-indigo-600 text-white">
            <div className="flex items-center gap-2">
              <Bot size={18} />
              <span className="font-semibold text-sm">Assistente CorbanPlus</span>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="hover:text-indigo-200 transition-colors"
            >
              <X size={18} />
            </button>
          </div>

          {/* Mensagens */}
          <div className="flex-1 overflow-y-auto px-4 py-4 min-h-0">
            {messages.length === 0 ? (
              <div className="space-y-4">
                <div className="flex items-start gap-2">
                  <div className="h-7 w-7 rounded-full bg-indigo-600 flex items-center justify-center shrink-0 mt-0.5">
                    <Bot size={14} className="text-white" />
                  </div>
                  <div className="bg-gray-100 rounded-2xl rounded-tl-sm px-3.5 py-2.5 text-sm text-gray-800 leading-relaxed">
                    Olá! Sou o assistente do CorbanPlus. Como posso te ajudar hoje?
                  </div>
                </div>
                <p className="text-xs text-gray-400 text-center">Sugestões rápidas:</p>
                <div className="space-y-2">
                  {suggestions.map((s) => (
                    <button
                      key={s}
                      onClick={() => { setInput(s); inputRef.current?.focus(); }}
                      className="w-full text-left text-xs text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded-lg px-3 py-2 transition-colors"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg) => <Message key={msg.id} msg={msg} />)
            )}
            {loading && (
              <div className="flex items-center gap-2 text-gray-400 text-sm">
                <div className="h-7 w-7 rounded-full bg-indigo-600 flex items-center justify-center shrink-0">
                  <Loader2 size={14} className="text-white animate-spin" />
                </div>
                <span className="text-xs">Pensando...</span>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="border-t border-gray-100 px-3 py-2 flex items-end gap-2">
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Escreva uma mensagem..."
              className="flex-1 resize-none rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 max-h-28"
              style={{ minHeight: '40px' }}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              className="h-9 w-9 rounded-xl bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40 transition-all flex items-center justify-center shrink-0"
            >
              <Send size={15} />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
