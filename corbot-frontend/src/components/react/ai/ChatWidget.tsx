import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Bot, X, Send, Loader2, MessageSquare, ChevronDown,
  MapPin, Paperclip, FileText, Image as ImageIcon, XCircle, Bell,
} from 'lucide-react';
import { api, API_BASE_URL, refreshAccessToken } from '../../../lib/api/client';
import { $tokens } from '../../../lib/stores/auth';
import { pendingTour } from '../../../lib/tour/store';
import { TOURS } from '../../../lib/tour/tours';
import type { AiConversation, AiMessage } from '../../../lib/api/types';
import { ENDPOINTS } from '../../../lib/api/endpoints';
import toast from 'react-hot-toast';

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
    <div className="relative inline-flex items-center gap-1.5 bg-[var(--color-primary-bg)] border border-[var(--color-primary)]/25 rounded-lg px-2 py-1 text-xs text-[var(--color-primary-dark)] max-w-full">
      {isImage && preview ? (
        <img src={preview} alt="" className="h-8 w-8 object-cover rounded" />
      ) : (
        <FileText size={14} />
      )}
      <span className="truncate max-w-[140px]">{file.name}</span>
      <button onClick={onRemove} className="text-[var(--color-primary)]/50 hover:text-[var(--color-primary-dark)] ml-0.5">
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
        <div className="h-7 w-7 rounded-full bg-[var(--color-primary)] flex items-center justify-center mr-2 shrink-0 mt-0.5">
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
              className="flex items-center gap-1.5 text-xs text-[var(--color-primary)] underline bg-[var(--color-primary-bg)] px-3 py-1.5 rounded-lg border border-[var(--color-primary)]/15"
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
                ? 'bg-[var(--color-primary)] text-white rounded-tr-sm'
                : 'bg-gray-100 text-gray-800 rounded-tl-sm'
            }`}
          >
            {renderContent(msg.content, isUser)}
          </div>
        )}
        {/* Botão tour */}
        {!isUser && msg.tour_name && TOURS[msg.tour_name] && (
          <button
            onClick={handleStartTour}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-full bg-[var(--color-primary-bg)] text-[var(--color-primary-dark)] hover:bg-[var(--color-primary-bg)] border border-[var(--color-primary)]/25 transition-colors"
          >
            <MapPin size={12} />
            Iniciar tour
          </button>
        )}
      </div>
    </div>
  );
}

const API_BASE_URL_FOR_MEDIA = (typeof API_BASE_URL === 'string' && API_BASE_URL)
  ? API_BASE_URL.replace(/\/api\/?$/, '')
  : '';

/** Renderiza negrito (**texto**) e links ([texto](url)) num parágrafo. */
function renderInline(text: string, isUser: boolean): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  // combina **bold** e [label](url) num único passe
  const re = /\*\*(.+?)\*\*|\[([^\]]+)\]\(([^)]+)\)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    if (m[1] !== undefined) {
      // **bold**
      parts.push(<strong key={m.index}>{m[1]}</strong>);
    } else {
      // [label](url)
      const href = m[3].startsWith('/') ? `${API_BASE_URL_FOR_MEDIA}${m[3]}` : m[3];
      parts.push(
        <a key={m.index} href={href} target="_blank" rel="noopener noreferrer"
          className={`underline ${isUser ? 'text-white/80 hover:text-white' : 'text-[var(--color-primary)] hover:text-[var(--color-primary-dark)]'}`}>
          {m[2]}
        </a>
      );
    }
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

function renderContent(text: string, isUser: boolean): React.ReactNode {
  return text.split('\n').map((line, i, arr) => (
    <span key={i}>{renderInline(line, isUser)}{i < arr.length - 1 ? '\n' : null}</span>
  ));
}

const LS_CONV_KEY = 'corbanplus_conv_id';
const LS_POS_KEY = 'corbanplus_assistant_pos';

export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [messages, setMessages] = useState<AiMessage[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(() => {
    const saved = localStorage.getItem(LS_CONV_KEY);
    return saved ? Number(saved) : null;
  });
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  // Evita corrida que abria múltiplas conexões (cada uma duplicava as respostas)
  const connectingRef = useRef(false);

  // Estado da tarefa em segundo plano (importação de arquivo grande)
  const [bgTask, setBgTask] = useState<{ convId: number; done: number; total: number } | null>(() => {
    try { return JSON.parse(localStorage.getItem('corbanplus_bg_task') || 'null'); } catch { return null; }
  });
  const [hasNotification, setHasNotification] = useState(
    () => localStorage.getItem('corbanplus_notif') === '1'
  );

  // ── Posição arrastável do botão flutuante ───────────────────────────────
  const fabRef = useRef<HTMLDivElement>(null);
  const dragStartRef = useRef<{ x: number; y: number; posX: number; posY: number } | null>(null);
  const draggedRef = useRef(false);
  const marginsRef = useRef({ right: 24, bottom: 24 });
  const [isDragging, setIsDragging] = useState(false);
  const [pos, setPos] = useState<{ x: number; y: number }>(() => {
    if (typeof window === 'undefined') return { x: 0, y: 0 };
    try {
      const saved = localStorage.getItem(LS_POS_KEY);
      if (saved) {
        const p = JSON.parse(saved);
        if (typeof p.x === 'number' && typeof p.y === 'number') return p;
      }
    } catch {
      // fallback silencioso
    }
    return { x: 0, y: 0 };
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;
    localStorage.setItem(LS_POS_KEY, JSON.stringify(pos));
  }, [pos]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    function updateMargins() {
      const isMobile = window.innerWidth < 768;
      let bottomMargin = 24;
      if (isMobile) {
        const navHeight = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--bottom-nav-height')) || 64;
        bottomMargin = navHeight + 12;
      }
      marginsRef.current = { right: isMobile ? 16 : 24, bottom: bottomMargin };
    }
    updateMargins();
    window.addEventListener('resize', updateMargins);
    return () => window.removeEventListener('resize', updateMargins);
  }, []);

  function handlePointerDown(e: React.PointerEvent<HTMLDivElement>) {
    const target = e.currentTarget;
    target.setPointerCapture(e.pointerId);
    draggedRef.current = false;
    const isMobile = window.innerWidth < 768;
    let bottomMargin = 24;
    if (isMobile) {
      const navHeight = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--bottom-nav-height')) || 64;
      bottomMargin = navHeight + 12;
    }
    marginsRef.current = { right: isMobile ? 16 : 24, bottom: bottomMargin };
    dragStartRef.current = { x: e.clientX, y: e.clientY, posX: pos.x, posY: pos.y };
  }

  function handlePointerMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!dragStartRef.current) return;
    const dx = e.clientX - dragStartRef.current.x;
    const dy = e.clientY - dragStartRef.current.y;
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
      draggedRef.current = true;
      setIsDragging(true);
    }
    const isMobile = window.innerWidth < 768;
    const maxX = isMobile ? 0 : window.innerWidth - 48 - marginsRef.current.right;
    const maxY = window.innerHeight - 48 - marginsRef.current.bottom;
    const rawX = dragStartRef.current.posX + dx;
    const rawY = dragStartRef.current.posY + dy;
    const nextX = isMobile ? 0 : Math.max(-maxX, Math.min(0, rawX));
    const nextY = Math.max(-maxY, Math.min(0, rawY));
    setPos({ x: nextX, y: nextY });
  }

  function handlePointerUp(e: React.PointerEvent<HTMLDivElement>) {
    const target = e.currentTarget;
    target.releasePointerCapture(e.pointerId);
    dragStartRef.current = null;
    const wasDrag = draggedRef.current;
    draggedRef.current = false;
    setIsDragging(false);
    if (!wasDrag) {
      setOpen((o) => !o);
      if (hasNotification) {
        setHasNotification(false);
        localStorage.removeItem('corbanplus_notif');
      }
    }
  }

  // ── WebSocket ───────────────────────────────────────────────────────────
  const connectWs = useCallback(() => {
    // Já existe conexão aberta/abrindo, ou outra tentativa em andamento? aborta.
    // Sem isso, a corrida no refresh assíncrono abria várias conexões e cada
    // uma entregava a mesma resposta (mensagens duplicadas 2x/3x).
    if (wsRef.current && wsRef.current.readyState <= WebSocket.OPEN) return;
    if (connectingRef.current) return;
    connectingRef.current = true;

    // Deriva URL ws:// / wss:// a partir de API_BASE_URL
    const wsBase = API_BASE_URL
      ? API_BASE_URL.replace(/^http/, 'ws')
      : (window.location.protocol === 'https:' ? 'wss' : 'ws') + '://' + window.location.host;

    // Sempre tenta renovar o access token antes de conectar para evitar
    // "Token is expired" no handshake WebSocket
    refreshAccessToken().then((freshToken) => {
      // Se refresh falhou, não tenta conectar com token expirado
      const token = freshToken;
      if (!token) { connectingRef.current = false; return; }

      // Fecha qualquer conexão remanescente antes de abrir a nova
      if (wsRef.current) { try { wsRef.current.close(); } catch { /* noop */ } }

      const ws = new WebSocket(`${wsBase}/ws/ai/chat/?token=${token}`);
      wsRef.current = ws;
      ws.onopen = () => { connectingRef.current = false; };
      ws.onerror = () => { connectingRef.current = false; };

      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);
          if (data.type === 'ai_reply') {
            setLoading(false);
            if ((data.reply ?? '').trim()) {
              setMessages((prev) => {
                // Proteção contra entrega duplicada (mesma resposta por mais
                // de uma conexão): ignora se o message_id já estiver na lista.
                if (data.message_id != null && prev.some((m) => m.id === data.message_id)) {
                  return prev;
                }
                return [...prev, {
                  id: data.message_id ?? Date.now(),
                  role: 'assistant',
                  content: data.reply ?? '',
                  tool_calls: null,
                  created_at: new Date().toISOString(),
                  tour_name: data.tour_name ?? null,
                }];
              });
            }
            if (data.task_complete) {
              setBgTask(null);
              localStorage.removeItem('corbanplus_bg_task');
              setHasNotification(true);
              localStorage.setItem('corbanplus_notif', '1');
            }
          } else if (data.type === 'ai_error') {
            setLoading(false);
            setMessages((prev) => [...prev, {
              id: Date.now(),
              role: 'assistant',
              content: data.error ?? 'Ocorreu um erro. Tente novamente.',
              tool_calls: null,
              created_at: new Date().toISOString(),
            }]);
            // Se havia uma tarefa em segundo plano, encerra a barra/anel e
            // notifica (sininho) que ela terminou — mesmo com erro.
            if (localStorage.getItem('corbanplus_bg_task')) {
              setBgTask(null);
              localStorage.removeItem('corbanplus_bg_task');
              setHasNotification(true);
              localStorage.setItem('corbanplus_notif', '1');
            }
          } else if (data.type === 'ai_progress') {
            const next = { convId: data.conversation_id, done: data.done ?? 0, total: data.total ?? 0 };
            setBgTask(next);
            localStorage.setItem('corbanplus_bg_task', JSON.stringify(next));
          }
        } catch {
          // ignora mensagens malformadas
        }
      };

      ws.onclose = () => {
        connectingRef.current = false;
        // Reconecta se o WS cair (apenas se esta ainda for a conexão ativa)
        if (wsRef.current === ws) {
          wsRef.current = null;
          setTimeout(connectWs, 1000);
        }
      };
    }).catch(() => { connectingRef.current = false; });
  }, []);

  // Conecta WebSocket ao montar; desconecta ao desmontar
  useEffect(() => {
    connectWs();
    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connectWs]);

  // Reconecta o WS quando o usuário faz login (tokens mudam de null → válido)
  useEffect(() => {
    const unsub = $tokens.subscribe((tokens) => {
      if (tokens?.access && (!wsRef.current || wsRef.current.readyState > WebSocket.OPEN)) {
        connectWs();
      }
    });
    return unsub;
  }, [connectWs]);

  // Carrega histórico quando o chat é aberto e há conversa salva
  useEffect(() => {
    if (!open || messages.length > 0 || !conversationId) return;
    setHistoryLoading(true);
    api.get<AiConversation>(`${ENDPOINTS.AI_CONVERSATIONS}${conversationId}/`)
      .then((data) => {
        if (data.messages?.length) {
          setMessages(data.messages);
        }
      })
      .catch(() => {
        // Conversa inválida ou deletada — começa nova
        localStorage.removeItem(LS_CONV_KEY);
        setConversationId(null);
      })
      .finally(() => setHistoryLoading(false));
  }, [open]);

  useEffect(() => {
    if (open) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
      inputRef.current?.focus();
    }
  }, [open, messages.length]);

  async function ensureConversation(): Promise<number> {
    if (conversationId) return conversationId;
    const data = await api.post<AiConversation>(ENDPOINTS.AI_CONVERSATIONS, {});
    setConversationId(data.id);
    localStorage.setItem(LS_CONV_KEY, String(data.id));
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

      if (pendingFile) {
        const fd = new FormData();
        if (text) fd.append('content', text);
        fd.append('file', pendingFile);
        await api.upload<{ status?: string; conversation_id?: number }>(
          `${ENDPOINTS.AI_CONVERSATIONS}${convId}/message/`, fd
        );
        // Todo upload de arquivo (imagem, PDF, CSV/Excel pequeno ou grande) é
        // uma tarefa em segundo plano: mostra a barra/anel imediatamente. O
        // backend envia `ai_progress` (arquivo grande) e `task_complete` ao
        // concluir, o que dispara o sininho. Texto puro não passa por aqui.
        const task = { convId, done: 0, total: 0 };
        setBgTask(task);
        localStorage.setItem('corbanplus_bg_task', JSON.stringify(task));
        setLoading(false);
      } else {
        await api.post(`${ENDPOINTS.AI_CONVERSATIONS}${convId}/message/`, { content: text });
      }
      // Resposta chegará via WebSocket — não fazemos nada aqui
    } catch {
      setLoading(false);
      setMessages((prev) => [...prev, {
        id: Date.now() + 2,
        role: 'assistant',
        content: 'Desculpe, ocorreu um erro. Tente novamente.',
        tool_calls: null,
        created_at: new Date().toISOString(),
      }]);
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
      toast.error(`Arquivo muito grande. Máximo: ${MAX_FILE_MB}MB`);
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
      {/* Botão flutuante (arrastável) */}
      <div
        ref={fabRef}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setOpen((o) => !o);
            if (hasNotification) {
              setHasNotification(false);
              localStorage.removeItem('corbanplus_notif');
            }
          }
        }}
        role="button"
        tabIndex={0}
        aria-label="Abrir assistente"
        data-tour="chat-widget-btn"
        className={`fixed bottom-6 right-6 max-md:bottom-[calc(var(--bottom-nav-height)+0.75rem)] max-md:right-4 z-50 h-12 w-12 rounded-full text-white shadow-lg transition-all flex items-center justify-center touch-none select-none cursor-grab ${
          isDragging ? 'cursor-grabbing' : ''
        } ${
          hasNotification ? 'bg-yellow-500 hover:bg-yellow-600' : 'bg-[var(--color-primary)] hover:opacity-90'
        }`}
        style={{
          transform: `translate3d(${pos.x}px, ${pos.y}px, 0)`,
          WebkitTransform: `translate3d(${pos.x}px, ${pos.y}px, 0)`,
        }}
      >
        {open ? (
          <ChevronDown size={22} />
        ) : hasNotification ? (
          <Bell size={22} />
        ) : (
          <MessageSquare size={22} />
        )}
      </div>

      {/* Ring de progresso flutuante — segue o botão */}
      {!open && bgTask && (
        <div
          className="fixed bottom-6 right-6 max-md:bottom-[calc(var(--bottom-nav-height)+0.75rem)] max-md:right-4 z-[51] pointer-events-none"
          style={{
            width: 48,
            height: 48,
            transform: `translate3d(${pos.x}px, ${pos.y}px, 0)`,
            WebkitTransform: `translate3d(${pos.x}px, ${pos.y}px, 0)`,
          }}
        >
          {bgTask.total > 0 ? (
            <svg viewBox="0 0 56 56" width="56" height="56"
                 style={{ transform: 'rotate(-90deg)' }}>
              <circle cx="28" cy="28" r="24" fill="none"
                      stroke="rgba(255,255,255,0.25)" strokeWidth="3" />
              <circle cx="28" cy="28" r="24" fill="none"
                      stroke="white" strokeWidth="3" strokeLinecap="round"
                      strokeDasharray={`${2 * Math.PI * 24}`}
                      strokeDashoffset={`${2 * Math.PI * 24 * (1 - Math.min(bgTask.done / bgTask.total, 1))}`}
                      style={{ transition: 'stroke-dashoffset 0.5s ease-out' }} />
            </svg>
          ) : (
            <svg viewBox="0 0 56 56" width="56" height="56"
                 className="animate-spin">
              <circle cx="28" cy="28" r="24" fill="none"
                      stroke="rgba(255,255,255,0.25)" strokeWidth="3" />
              <circle cx="28" cy="28" r="24" fill="none"
                      stroke="white" strokeWidth="3" strokeLinecap="round"
                      strokeDasharray="40 110" />
            </svg>
          )}
        </div>
      )}

      {/* Painel do chat */}
      {open && (
        <div
          className="fixed bottom-24 right-6 max-md:bottom-[calc(var(--bottom-nav-height)+4.5rem)] max-md:right-3 max-md:left-3 z-50 w-[360px] max-md:w-auto rounded-2xl bg-white shadow-2xl border border-gray-200 flex flex-col overflow-hidden"
          style={{
            maxHeight: 'min(580px, calc(100vh - 120px))',
            transform: `translate3d(${pos.x}px, ${pos.y}px, 0)`,
            WebkitTransform: `translate3d(${pos.x}px, ${pos.y}px, 0)`,
          }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 bg-[var(--color-primary)] text-white">
            <div className="flex items-center gap-2">
              <Bot size={18} />
              <span className="font-semibold text-sm">Assistente CorbanPlus</span>
            </div>
            <button onClick={() => setOpen(false)} className="hover:text-white/80 transition-colors">
              <X size={18} />
            </button>
          </div>

          {/* Mensagens */}
          <div className="flex-1 overflow-y-auto px-4 py-4 min-h-0">
            {historyLoading ? (
              <div className="flex items-center justify-center h-full text-gray-400 gap-2">
                <Loader2 size={16} className="animate-spin" />
                <span className="text-xs">Carregando histórico...</span>
              </div>
            ) : messages.length === 0 ? (
              <div className="space-y-4">
                <div className="flex items-start gap-2">
                  <div className="h-7 w-7 rounded-full bg-[var(--color-primary)] flex items-center justify-center shrink-0 mt-0.5">
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
                      className="w-full text-left text-xs text-[var(--color-primary-dark)] bg-[var(--color-primary-bg)] hover:bg-[var(--color-primary-bg)] rounded-lg px-3 py-2 transition-colors"
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
                <div className="h-7 w-7 rounded-full bg-[var(--color-primary)] flex items-center justify-center shrink-0">
                  <Loader2 size={14} className="text-white animate-spin" />
                </div>
                <span className="text-xs">Pensando...</span>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Barra de progresso — tarefa em segundo plano */}
          {bgTask && (
            <div className="px-4 py-2.5 border-t border-[var(--color-primary)]/15 bg-[var(--color-primary-bg)] shrink-0">
              <div className="flex items-center justify-between text-xs text-[var(--color-primary)] mb-1.5">
                <span className="font-medium">Criando tabelas…</span>
                {bgTask.total > 0 && (
                  <span className="tabular-nums">{bgTask.done}/{bgTask.total} lotes</span>
                )}
              </div>
              <div className="h-1.5 bg-[var(--color-primary)]/20 rounded-full overflow-hidden">
                {bgTask.total > 0 ? (
                  <div
                    className="h-full bg-[var(--color-primary-bg)]0 rounded-full"
                    style={{
                      width: `${Math.round((bgTask.done / bgTask.total) * 100)}%`,
                      transition: 'width 0.5s ease-out',
                    }}
                  />
                ) : (
                  <div className="h-full bg-[var(--color-primary-bg)]0 rounded-full animate-pulse w-full" />
                )}
              </div>
            </div>
          )}

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
              className="h-9 w-9 rounded-xl text-gray-400 hover:text-[var(--color-primary)] hover:bg-[var(--color-primary-bg)] transition-all flex items-center justify-center shrink-0"
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
              className="flex-1 resize-none rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]/40 max-h-28"
              style={{ minHeight: '40px' }}
            />
            <button
              onClick={handleSend}
              disabled={(!input.trim() && !file) || loading}
              className="h-9 w-9 rounded-xl bg-[var(--color-primary)] text-white hover:opacity-90 disabled:opacity-40 transition-all flex items-center justify-center shrink-0"
            >
              <Send size={15} />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
