import { useState, useRef, useEffect, useCallback } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { Upload, Download, CheckCircle, XCircle, Loader2, AlertCircle } from 'lucide-react';
import clsx from 'clsx';
import { PageHeader } from '../../ui/PageHeader';
import { Modal } from '../../ui/Modal';
import { Button } from '../../ui/Button';

type EntityType = 'vendedor' | 'lider' | 'gerente' | 'corban' | 'bank_access';

interface ImportJob {
  job_id: string;
  entity_type: EntityType;
  status: 'pending' | 'processing' | 'done' | 'failed';
  total_rows: number;
  processed_rows: number;
  created_count: number;
  updated_count: number;
  error_count: number;
  progress_pct: number;
  errors: { linha: number; dado: string; erro: string }[];
  has_error_report?: boolean;
  created_at: string;
  update_existing: boolean;
}

const DISMISSED_STORAGE_KEY = 'corbot_import_dismissed';

const TABS: { type: EntityType; label: string; description: string; requiredFields: string[] }[] = [
  {
    type: 'vendedor',
    label: 'Vendedores',
    description:
      'Importa vendedores em lote. Pela promotora, cada linha deve ter cpf_corban (CPF do admin do corban). Opcional: enrollment (matrícula; se vazio, usa o CPF).',
    requiredFields: ['cpf', 'email', 'first_name', 'password', 'cpf_corban', 'pix_key', 'pix_type'],
  },
  {
    type: 'lider',
    label: 'Líderes',
    description:
      'Importa líderes em lote. Pela promotora, cpf_corban é obrigatório. Opcional: enrollment (matrícula).',
    requiredFields: ['cpf', 'email', 'first_name', 'password', 'cpf_corban'],
  },
  {
    type: 'gerente',
    label: 'Gerentes',
    description:
      'Importa gerentes em lote. Pela promotora, cpf_corban é obrigatório. Opcional: enrollment (matrícula).',
    requiredFields: ['cpf', 'email', 'first_name', 'password', 'cpf_corban'],
  },
  {
    type: 'corban',
    label: 'Corbans',
    description: 'Importa corbans e cria o admin de cada um. Opcional: admin_enrollment (matrícula do admin). Também aceita admin_pix_key e admin_pix_type.',
    requiredFields: ['name', 'document', 'admin_cpf', 'admin_email', 'admin_first_name', 'admin_password'],
  },
  {
    type: 'bank_access',
    label: 'Acessos',
    description: 'Importa acessos bancários. Use is_master=true para perfil Corban (comissão direta) ou false para vendedor. Bancos com login CPF: um acesso por usuário. Opcional: notes, link.',
    requiredFields: ['cpf', 'bank_name', 'username', 'password', 'is_active'],
  },
];

function loadDismissedIds(): Set<string> {
  try {
    const raw = sessionStorage.getItem(DISMISSED_STORAGE_KEY);
    if (!raw) return new Set();
    return new Set(JSON.parse(raw) as string[]);
  } catch {
    return new Set();
  }
}

function saveDismissedIds(ids: Set<string>) {
  sessionStorage.setItem(DISMISSED_STORAGE_KEY, JSON.stringify([...ids]));
}

function isJobActive(job: ImportJob) {
  return job.status === 'pending' || job.status === 'processing';
}

function mergeJobs(existing: ImportJob[], incoming: ImportJob[]): ImportJob[] {
  // Map.set sobrescreve por chave; iteramos existing primeiro e incoming
  // depois para que os jobs novos (vindos do polling) substituam os antigos.
  // Antes a ordem estava invertida e o estado nunca atualizava após o
  // primeiro fetch — polling funcionava mas a UI ficava congelada.
  const map = new Map<string, ImportJob>();
  for (const job of [...existing, ...incoming]) {
    map.set(job.job_id, job);
  }
  return Array.from(map.values()).sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );
}

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

async function downloadErrorReport(jobId: string, entityType: string) {
  const { blob, filename } = await api.getBlob(ENDPOINTS.IMPORT_ERRORS_XLSX(jobId));
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename || `import_erros_${entityType}_${jobId}.xlsx`;
  a.click();
  URL.revokeObjectURL(url);
}

function JobCard({ job, onDismiss }: { job: ImportJob; onDismiss: () => void }) {
  const isDone = job.status === 'done';
  const isFailed = job.status === 'failed';
  const isActive = isJobActive(job);
  const [downloadingErrors, setDownloadingErrors] = useState(false);
  const [downloadError, setDownloadError] = useState('');

  async function handleDownloadErrors() {
    setDownloadingErrors(true);
    setDownloadError('');
    try {
      await downloadErrorReport(job.job_id, job.entity_type);
    } catch {
      setDownloadError('Não foi possível baixar o log de erros.');
    } finally {
      setDownloadingErrors(false);
    }
  }

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

      <div className="flex flex-wrap gap-4 text-sm text-[var(--color-text-muted)]">
        <span><strong className="text-[var(--color-text)]">{job.processed_rows}</strong>/{job.total_rows} linhas</span>
        <span className="text-[var(--color-success)]"><strong>{job.created_count}</strong> criados</span>
        {(job.updated_count ?? 0) > 0 && (
          <span className="text-blue-600"><strong>{job.updated_count}</strong> atualizados</span>
        )}
        {job.error_count > 0 && (
          <span className="text-[var(--color-error)]"><strong>{job.error_count}</strong> erros</span>
        )}
      </div>

      {(job.error_count > 0 || job.has_error_report) && (
        <div className="space-y-2">
          <button
            type="button"
            onClick={handleDownloadErrors}
            disabled={downloadingErrors}
            className="inline-flex items-center gap-2 text-xs font-medium text-[var(--color-primary)] hover:underline disabled:opacity-50"
          >
            {downloadingErrors ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
            Baixar log de erros (Excel)
          </button>
          {downloadError && (
            <p className="text-xs text-[var(--color-error)]">{downloadError}</p>
          )}
        </div>
      )}

      {(job.errors ?? []).length > 0 && (
        <details className="text-xs">
          <summary className="cursor-pointer text-[var(--color-error)] font-medium">
            Ver erros na tela ({job.errors.length})
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

interface TabPanelProps {
  tab: typeof TABS[0];
  jobs: ImportJob[];
  onJobCreated: (job: ImportJob) => void;
  onDismissJob: (jobId: string) => void;
}

function TabPanel({ tab, jobs, onJobCreated, onDismissJob }: TabPanelProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [confirmOpen, setConfirmOpen] = useState(false);

  function openConfirm() {
    if (!file) return;
    setError('');
    setConfirmOpen(true);
  }

  async function performUpload(updateExisting: boolean) {
    if (!file) return;
    setConfirmOpen(false);
    setError('');
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('entity_type', tab.type);
      fd.append('update_existing', updateExisting ? 'true' : 'false');
      const job = await api.upload<ImportJob>(ENDPOINTS.IMPORT_CREATE, fd);
      onJobCreated(job);
      setFile(null);
      if (fileRef.current) fileRef.current.value = '';
    } catch (e: unknown) {
      const msg = (e as { data?: { error?: string } })?.data?.error || 'Erro ao enviar arquivo.';
      setError(msg);
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

      <div className="flex flex-wrap gap-2">
        {tab.requiredFields.map(f => (
          <span key={f} className="text-xs bg-[var(--color-primary-bg)] text-[var(--color-primary)] px-2 py-0.5 rounded-full font-mono">
            {f} *
          </span>
        ))}
      </div>

      <div
        data-tour="csv-upload-area"
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

      <div className="flex gap-3">
        <button
          onClick={openConfirm}
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

      {jobs.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-[var(--color-text)]">Importações recentes</h3>
          {jobs.map(job => (
            <JobCard
              key={job.job_id}
              job={job}
              onDismiss={() => onDismissJob(job.job_id)}
            />
          ))}
        </div>
      )}

      <Modal
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title="Atualizar cadastros existentes?"
      >
        <div className="space-y-4">
          <p className="text-sm text-[var(--color-text-muted)]">
            Se houver registros que já existem no sistema (mesmo CPF, documento ou banco),
            o que devemos fazer?
          </p>
          <ul className="text-xs text-[var(--color-text-muted)] list-disc list-inside space-y-1">
            <li><strong className="text-[var(--color-text)]">Sim:</strong> sobrescreve os dados existentes com os do arquivo.</li>
            <li><strong className="text-[var(--color-text)]">Não:</strong> mantém os existentes e marca como erro de duplicado.</li>
          </ul>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="secondary"
              onClick={() => performUpload(false)}
            >
              Não
            </Button>
            <Button onClick={() => performUpload(true)}>
              Sim, atualizar
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

export function ImportPage() {
  const [activeTab, setActiveTab] = useState<EntityType>('vendedor');
  const [jobsByType, setJobsByType] = useState<Partial<Record<EntityType, ImportJob[]>>>({});
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(loadDismissedIds);
  const jobsByTypeRef = useRef(jobsByType);
  jobsByTypeRef.current = jobsByType;

  const active = TABS.find(t => t.type === activeTab)!;

  const filterVisible = useCallback((jobs: ImportJob[]) => {
    return jobs.filter(j => !dismissedIds.has(j.job_id) || isJobActive(j));
  }, [dismissedIds]);

  const loadJobsForType = useCallback(async (entityType: EntityType) => {
    try {
      const list = await api.get<ImportJob[]>(
        `${ENDPOINTS.IMPORT_CREATE}?entity_type=${entityType}&limit=15`,
      );
      setJobsByType(prev => ({
        ...prev,
        [entityType]: mergeJobs(prev[entityType] || [], list),
      }));
    } catch {
      // silencioso — polling tenta de novo
    }
  }, []);

  const pollActiveJobs = useCallback(async () => {
    const allJobs = Object.values(jobsByTypeRef.current).flat();
    const activeJobs = allJobs.filter(isJobActive);
    if (!activeJobs.length) return;

    await Promise.all(
      activeJobs.map(async (job) => {
        try {
          const updated = await api.get<ImportJob>(ENDPOINTS.IMPORT_STATUS(job.job_id));
          setJobsByType(prev => ({
            ...prev,
            [updated.entity_type]: mergeJobs(prev[updated.entity_type] || [], [updated]),
          }));
        } catch {
          // ignore
        }
      }),
    );
  }, []);

  useEffect(() => {
    loadJobsForType(activeTab);
  }, [activeTab, loadJobsForType]);

  useEffect(() => {
    const interval = setInterval(pollActiveJobs, 1500);
    return () => clearInterval(interval);
  }, [pollActiveJobs]);

  useEffect(() => {
    function onVisible() {
      if (document.visibilityState !== 'visible') return;
      loadJobsForType(activeTab);
      pollActiveJobs();
    }
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  }, [activeTab, loadJobsForType, pollActiveJobs]);

  function handleJobCreated(job: ImportJob) {
    setDismissedIds(prev => {
      if (!prev.has(job.job_id)) return prev;
      const next = new Set(prev);
      next.delete(job.job_id);
      saveDismissedIds(next);
      return next;
    });
    setJobsByType(prev => ({
      ...prev,
      [job.entity_type]: mergeJobs(prev[job.entity_type] || [], [job]),
    }));
  }

  function handleDismissJob(jobId: string) {
    setJobsByType(prev => {
      const next = { ...prev };
      for (const type of Object.keys(next) as EntityType[]) {
        next[type] = (next[type] || []).filter(j => j.job_id !== jobId);
      }
      return next;
    });
    setDismissedIds(prev => {
      const next = new Set(prev);
      next.add(jobId);
      saveDismissedIds(next);
      return next;
    });
  }

  const visibleJobs = filterVisible(jobsByType[activeTab] || []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Importação em lote"
        subtitle="Importe vendedores, líderes, gerentes, corbans e acessos bancários via CSV ou XLSX com acompanhamento em tempo real."
      />

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

      <div className="bg-[var(--color-card-bg)] border border-[var(--color-border)] rounded-2xl p-6">
        <TabPanel
          tab={active}
          jobs={visibleJobs}
          onJobCreated={handleJobCreated}
          onDismissJob={handleDismissJob}
        />
      </div>
    </div>
  );
}
