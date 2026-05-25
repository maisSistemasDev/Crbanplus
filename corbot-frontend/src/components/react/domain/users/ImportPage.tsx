import { useState, useRef, useEffect } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { Upload, Download, CheckCircle, XCircle, Loader2, AlertCircle } from 'lucide-react';
import clsx from 'clsx';

type EntityType = 'vendedor' | 'lider' | 'gerente' | 'corban' | 'bank_access';

interface ImportJob {
  job_id: string;
  entity_type: EntityType;
  status: 'pending' | 'processing' | 'done' | 'failed';
  total_rows: number;
  processed_rows: number;
  created_count: number;
  error_count: number;
  progress_pct: number;
  errors: { linha: number; dado: string; erro: string }[];
  created_at: string;
}

const TABS: { type: EntityType; label: string; description: string; requiredFields: string[] }[] = [
  {
    type: 'vendedor',
    label: 'Vendedores',
    description: 'Importa vendedores em lote. Campos obrigatórios: cpf, email, first_name, password.',
    requiredFields: ['cpf', 'email', 'first_name', 'password', 'pix_key', 'pix_type'],
  },
  {
    type: 'lider',
    label: 'Líderes',
    description: 'Importa líderes em lote. Campos obrigatórios: cpf, email, first_name, password.',
    requiredFields: ['cpf', 'email', 'first_name', 'password'],
  },
  {
    type: 'gerente',
    label: 'Gerentes',
    description: 'Importa gerentes em lote. Campos obrigatórios: cpf, email, first_name, password.',
    requiredFields: ['cpf', 'email', 'first_name', 'password'],
  },
  {
    type: 'corban',
    label: 'Corbans',
    description: 'Importa corbans e cria automaticamente um usuário administrador para cada um. Campos obrigatórios: name, document, admin_cpf, admin_email, admin_first_name, admin_password.',
    requiredFields: ['name', 'document', 'admin_cpf', 'admin_email', 'admin_first_name', 'admin_password'],
  },
  {
    type: 'bank_access',
    label: 'Acessos',
    description: 'Importa acessos bancários em lote. O vínculo é feito pelo CPF do usuário. Campos obrigatórios: cpf, bank_name, username, password.',
    requiredFields: ['cpf', 'bank_name', 'username', 'password', 'is_active'],
  },
];

function ProgressBar({ pct }: { pct: number }) {
  return (
    <div className="w-full bg-[var(--color-border)] rounded-full h-3 overflow-hidden">
      <div
        className="h-3 rounded-full bg-[var(--color-primary)] transition-all duration-300"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function JobCard({ job, onDismiss }: { job: ImportJob; onDismiss: () => void }) {
  const isDone = job.status === 'done';
  const isFailed = job.status === 'failed';
  const isActive = job.status === 'processing' || job.status === 'pending';

  return (
    <div className="bg-[var(--color-card-bg)] border border-[var(--color-border)] rounded-xl p-5 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isActive && <Loader2 size={18} className="animate-spin text-[var(--color-primary)]" />}
          {isDone && <CheckCircle size={18} className="text-[var(--color-success)]" />}
          {isFailed && <XCircle size={18} className="text-[var(--color-error)]" />}
          <span className="font-semibold text-sm capitalize">{job.entity_type}</span>
          <span
            className={clsx(
              'text-xs px-2 py-0.5 rounded-full font-medium',
              isActive && 'bg-blue-100 text-blue-700',
              isDone && 'bg-green-100 text-green-700',
              isFailed && 'bg-red-100 text-red-700',
            )}
          >
            {job.status === 'pending' ? 'Aguardando' :
             job.status === 'processing' ? 'Processando' :
             job.status === 'done' ? 'Concluído' : 'Falhou'}
          </span>
        </div>
        {(isDone || isFailed) && (
          <button onClick={onDismiss} className="text-[var(--color-text-muted)] hover:text-[var(--color-text)] text-xs">
            Fechar
          </button>
        )}
      </div>

      <ProgressBar pct={job.progress_pct} />

      <div className="flex gap-4 text-sm text-[var(--color-text-muted)]">
        <span><strong className="text-[var(--color-text)]">{job.processed_rows}</strong>/{job.total_rows} linhas</span>
        <span className="text-[var(--color-success)]"><strong>{job.created_count}</strong> criados</span>
        {job.error_count > 0 && (
          <span className="text-[var(--color-error)]"><strong>{job.error_count}</strong> erros</span>
        )}
      </div>

      {(job.errors ?? []).length > 0 && (
        <details className="text-xs">
          <summary className="cursor-pointer text-[var(--color-error)] font-medium">
            Ver erros ({job.errors.length})
          </summary>
          <div className="mt-2 max-h-48 overflow-y-auto border border-[var(--color-border)] rounded-lg divide-y divide-[var(--color-border)]">
            {job.errors.map((e, i) => (
              <div key={i} className="px-3 py-2">
                <span className="font-medium text-[var(--color-text-muted)]">Linha {e.linha}</span>
                {e.dado && <span className="mx-1 text-[var(--color-text-muted)]">· {e.dado}</span>}
                <span className="text-[var(--color-error)]">: {e.erro}</span>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

function TabPanel({ tab }: { tab: typeof TABS[0] }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [jobs, setJobs] = useState<ImportJob[]>([]);
  const pollingRefs = useRef<Record<string, ReturnType<typeof setInterval>>>({});

  // Poll a specific job until done/failed
  function startPolling(jobId: string) {
    if (pollingRefs.current[jobId]) return;
    pollingRefs.current[jobId] = setInterval(async () => {
      try {
        const updated = await api.get<ImportJob>(ENDPOINTS.IMPORT_STATUS(jobId));
        setJobs(prev => prev.map(j => j.job_id === jobId ? updated : j));
        if (updated.status === 'done' || updated.status === 'failed') {
          clearInterval(pollingRefs.current[jobId]);
          delete pollingRefs.current[jobId];
        }
      } catch {}
    }, 1500);
  }

  useEffect(() => {
    return () => {
      Object.values(pollingRefs.current).forEach(clearInterval);
    };
  }, []);

  async function handleUpload() {
    if (!file) return;
    setError('');
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('entity_type', tab.type);
      const job = await api.upload<ImportJob>(ENDPOINTS.IMPORT_CREATE, fd);
      setJobs(prev => [job, ...prev]);
      setFile(null);
      if (fileRef.current) fileRef.current.value = '';
      startPolling(job.job_id);
    } catch (e: any) {
      setError(e?.data?.error || 'Erro ao enviar arquivo.');
    } finally {
      setUploading(false);
    }
  }

  async function handleDownloadTemplate() {
    try {
      const { blob, filename } = await api.getBlob(ENDPOINTS.IMPORT_TEMPLATE(tab.type));
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || `template_${tab.type}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError('Erro ao baixar o template.');
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-[var(--color-text-muted)]">{tab.description}</p>

      {/* Required fields */}
      <div className="flex flex-wrap gap-2">
        {tab.requiredFields.map(f => (
          <span key={f} className="text-xs bg-[var(--color-primary-bg)] text-[var(--color-primary)] px-2 py-0.5 rounded-full font-mono">
            {f} *
          </span>
        ))}
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileRef.current?.click()}
        className={clsx(
          'border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors',
          dragging
            ? 'border-[var(--color-primary)] bg-[var(--color-primary-bg)]'
            : 'border-[var(--color-border)] hover:border-[var(--color-primary)]',
        )}
      >
        <Upload size={32} className="mx-auto mb-2 text-[var(--color-text-muted)]" />
        {file ? (
          <p className="text-sm font-medium text-[var(--color-text)]">{file.name}</p>
        ) : (
          <p className="text-sm text-[var(--color-text-muted)]">
            Arraste um arquivo CSV ou XLSX ou <span className="text-[var(--color-primary)] underline">clique para selecionar</span>
          </p>
        )}
        <input
          ref={fileRef}
          type="file"
          className="hidden"
          accept=".csv,.xlsx,.xls"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
      </div>

      {error && (
        <div className="flex items-center gap-2 text-sm text-[var(--color-error)] bg-red-50 border border-red-200 rounded-lg px-4 py-2">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className={clsx(
            'flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-medium text-white transition-colors',
            file && !uploading
              ? 'bg-[var(--color-primary)] hover:bg-[var(--color-primary-dark)]'
              : 'bg-[var(--color-border)] cursor-not-allowed text-[var(--color-text-muted)]',
          )}
        >
          {uploading ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
          {uploading ? 'Enviando...' : 'Importar'}
        </button>
        <button
          onClick={handleDownloadTemplate}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border border-[var(--color-border)] hover:bg-[var(--color-body-bg)] transition-colors text-[var(--color-text)]"
        >
          <Download size={16} />
          Baixar template CSV
        </button>
      </div>

      {/* Job cards */}
      {jobs.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-[var(--color-text)]">Importações recentes</h3>
          {jobs.map(job => (
            <JobCard
              key={job.job_id}
              job={job}
              onDismiss={() => setJobs(prev => prev.filter(j => j.job_id !== job.job_id))}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function ImportPage() {
  const [activeTab, setActiveTab] = useState<EntityType>('vendedor');
  const active = TABS.find(t => t.type === activeTab)!;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text)]">Importação em Lote</h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          Importe vendedores, líderes, gerentes, corbans e acessos bancários via CSV ou XLSX com acompanhamento em tempo real.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-[var(--color-body-bg)] p-1 rounded-xl border border-[var(--color-border)] w-fit">
        {TABS.map(tab => (
          <button
            key={tab.type}
            onClick={() => setActiveTab(tab.type)}
            className={clsx(
              'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              activeTab === tab.type
                ? 'bg-[var(--color-card-bg)] text-[var(--color-primary)] shadow-sm'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)]',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Panel */}
      <div className="bg-[var(--color-card-bg)] border border-[var(--color-border)] rounded-2xl p-6">
        <TabPanel key={activeTab} tab={active} />
      </div>
    </div>
  );
}
