import { useState, useRef, useEffect } from 'react';
import {
  Bot, X, Send, Loader2, MessageSquare, ChevronDown,
  MapPin, Paperclip, FileText, Image as ImageIcon, XCircle,
} from 'lucide-react';
import { pendingTour } from '../../../lib/tour/store';
import { TOURS } from '../../../lib/tour/tours';
import type { AiConversation, AiMessage } from '../../../lib/api/types';
import { ENDPOINTS } from '../../../lib/api/endpoints';

const ACCEPTED_TYPES = 'image/*,.pdf,.csv,.txt,.xlsx,.xls';
const MAX_FILE_MB = 10;

function FilePreview({ file, onRemove }: { file: File; onRemove: () => void }) {
  const isImage = file.type.startsWith('image/');
  const [preview, setPreview] = useState<string | null>(null);

  useEffect(() => {
    if (!isImage) return;
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file, isImage]);

  return (
    <div className="relative inline-flex items-center gap-1.5 bg-indigo-50 border border-indigo-200 rounded-lg px-2 py-1 text-xs text-indigo-700 max-w-full">
      {isImage && preview ? (
        <img src={preview} alt="" className="h-8 w-8 object-cover rounded" />
      ) : (
        <FileText size={14} />
      )}
      <span className="truncate max-w-[140px]">{file.name}</span>
      <button onClick={onRemove} className="text-indigo-400 hover:text-indigo-700 ml-0.5">
        <XCircle size={13} />
      </button>
    </div>
  );
}

function Message({ msg }: { msg: AiMessage }) {
  const isUser = msg.role === 'user';

  function handleStartTour() {
    if (!msg.tour_name) return;
    const steps = TOURS[msg.tour_name];
    if (steps) pendingTour.set(steps);
  }

  const isImage = msg.file_url && /\.(png|jpg|jpeg|gif|webp)$/i.test(msg.file_url);

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      {!isUser && (
        <div className="h-7 w-7 rounded-full bg-indigo-600 flex items-center justify-center mr-2 shrink-0 mt-0.5">
          <Bot size={14} className="text-white" />
        </div>
      )}
      <div className="max-w-[80%] flex flex-col gap-2 items-start">
        {/* Arquivo/imagem enviado */}
        {msg.file_url && (
          isImage ? (
            <img
              src={msg.file_url}
              alt={msg.file_name || 'imagem'}
              className="rounded-xl max-h-48 object-contain border border-gray-200"
            />
          ) : (
            <a
              href={msg.file_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-xs text-indigo-600 underline bg-indigo-50 px-3 py-1.5 rounded-lg border border-indigo-100"
            >
              <FileText size={13} />
              {msg.file_name || 'Arquivo'}
            </a>
          )
        )}
        {/* Texto */}
        {msg.content && !msg.content.startsWith('[Arquivo enviado:') && (
          <div
            className={`rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
              isUser
                ? 'bg-indigo-600 text-white rounded-tr-sm'
                : 'bg-gray-100 text-gray-800 rounded-tl-sm'
            }`}
          >
            {msg.content}
          </div>
        )}
        {/* Botão tour */}
        {!isUser && msg.tour_name && TOURS[msg.tour_name] && (
          <button
            onClick={handleStartTour}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-full bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 transition-colors"
          >
            <MapPin size={12} />
            Iniciar tour
          </button>
        )}
      </div>
    </div>
  );
}

export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [messages, setMessages] = useState<AiMessage[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
      inputRef.current?.focus();
    }
  }, [open, messages.length]);

  async function ensureConversation(): Promise<number> {
    if (conversationId) return conversationId;
    const token = localStorage.getItem('access_token');
    const res = await fetch(`/api${ENDPOINTS.AI_CONVERSATIONS}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({}),
    });
    const data = await res.json() as AiConversation;
    setConversationId(data.id);
    return data.id;
  }

  async function handleSend() {
    const text = input.trim();
    if ((!text && !file) || loading) return;

    const displayText = text || (file ? `Arquivo: ${file.name}` : '');

    const userMsg: AiMessage = {
      id: Date.now(),
      role: 'user',
      content: text || `[Arquivo enviado: ${file?.name}]`,
      tool_calls: null,
      created_at: new Date().toISOString(),
      file_url: file ? URL.createObjectURL(file) : undefined,
      file_name: file?.name,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    const pendingFile = file;
    setFile(null);
    setLoading(true);

    try {
      const convId = await ensureConversation();
      const token = localStorage.getItem('access_token');

      let res: { reply: string; tour_name: string | null; conversation_id: number };

      if (pendingFile) {
        const fd = new FormData();
        if (text) fd.append('content', text);
        fd.append('file', pendingFile);
        const r = await fetch(`/api${ENDPOINTS.AI_CONVERSATIONS}${convId}/message/`, {
          method: 'POST',
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: fd,
        });
        res = await r.json();
      } else {
        const r = await fetch(`/api${ENDPOINTS.AI_CONVERSATIONS}${convId}/message/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ content: text }),
        });
        res = await r.json();
      }

      const assistantMsg: AiMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: res.reply ?? '',
        tool_calls: null,
        created_at: new Date().toISOString(),
        tour_name: res.tour_name ?? null,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [...prev, {
        id: Date.now() + 2,
        role: 'assistant',
        content: 'Desculpe, ocorreu um erro. Tente novamente.',
        tool_calls: null,
        created_at: new Date().toISOString(),
      }]);
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

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > MAX_FILE_MB * 1024 * 1024) {
      alert(`Arquivo muito grande. Máximo: ${MAX_FILE_MB}MB`);
      return;
    }
    setFile(f);
    e.target.value = '';
  }

  const suggestions = [
    'Quais bancos estão ativos?',
    'Como criar uma equipe de comissão?',
    'Como aceitar uma sugestão de tabela?',
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
          style={{ maxHeight: 'min(580px, calc(100vh - 120px))' }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 bg-indigo-600 text-white">
            <div className="flex items-center gap-2">
              <Bot size={18} />
              <span className="font-semibold text-sm">Assistente CorbanPlus</span>
            </div>
            <button onClick={() => setOpen(false)} className="hover:text-indigo-200 transition-colors">
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
                    Olá! Sou o assistente do CorbanPlus. Posso consultar bancos, tabelas, convênios e ler imagens de tabelas bancárias. Como posso te ajudar?
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

          {/* Preview do arquivo selecionado */}
          {file && (
            <div className="px-3 pb-1">
              <FilePreview file={file} onRemove={() => setFile(null)} />
            </div>
          )}

          {/* Input */}
          <div className="border-t border-gray-100 px-3 py-2 flex items-end gap-2">
            {/* Botão de anexar */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              title="Anexar imagem ou arquivo"
              className="h-9 w-9 rounded-xl text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 transition-all flex items-center justify-center shrink-0"
            >
              <Paperclip size={17} />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_TYPES}
              className="hidden"
              onChange={handleFileChange}
            />

            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Escreva ou envie uma imagem..."
              className="flex-1 resize-none rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 max-h-28"
              style={{ minHeight: '40px' }}
            />
            <button
              onClick={handleSend}
              disabled={(!input.trim() && !file) || loading}
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
