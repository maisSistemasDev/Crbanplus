import { useState, useRef, useEffect } from 'react';
import { Modal } from '../../ui/Modal';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { Upload, Download, AlertCircle, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import clsx from 'clsx';

interface ImportJob {
  job_id: string;
  status: 'pending' | 'processing' | 'done' | 'failed';
  total_rows: number;
  processed_rows: number;
  created_count: number;
  error_count: number;
  progress_pct: number;
  errors: { linha: number; dado: string; erro: string }[];
}

interface BankCSVImportProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function BankCSVImport({ isOpen, onClose, onSuccess }: BankCSVImportProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [job, setJob] = useState<ImportJob | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function stopPolling() {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }

  function startPolling(jobId: string) {
    stopPolling();
    pollingRef.current = setInterval(async () => {
      try {
        const updated = await api.get<ImportJob>(ENDPOINTS.IMPORT_STATUS(jobId));
        setJob(updated);
        if (updated.status === 'done' || updated.status === 'failed') {
          stopPolling();
          if (updated.status === 'done' && updated.error_count === 0) {
            onSuccess();
          }
        }
      } catch {}
    }, 1500);
  }

  useEffect(() => {
    if (!isOpen) {
      stopPolling();
      setFile(null);
      setError('');
      setJob(null);
    }
    return stopPolling;
  }, [isOpen]);

  async function handleUpload() {
    if (!file) return;
    setError('');
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('entity_type', 'bank');
      const created = await api.upload<ImportJob>(ENDPOINTS.IMPORT_CREATE, fd);
      setJob(created);
      setFile(null);
      if (fileRef.current) fileRef.current.value = '';
      startPolling(created.job_id);
    } catch (e: any) {
      setError(e?.data?.error || 'Erro ao enviar arquivo.');
    } finally {
      setUploading(false);
    }
  }

  async function handleDownloadTemplate() {
    try {
      const { blob, filename } = await api.getBlob(ENDPOINTS.IMPORT_TEMPLATE('bank'));
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || 'template_bancos.csv';
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

  const isDone = job?.status === 'done';
  const isFailed = job?.status === 'failed';
  const isActive = job?.status === 'pending' || job?.status === 'processing';

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Importar Bancos via CSV">
      <div className="space-y-5">
        <p className="text-sm text-[var(--color-text-muted)]">
          Importe bancos em lote. Se o nome já existir, o registro será atualizado.
          Campos obrigatórios: <code className="text-xs bg-[var(--color-primary-bg)] text-[var(--color-primary)] px-1 rounded">name</code>.
          Opcionais: <code className="text-xs bg-[var(--color-primary-bg)] text-[var(--color-primary)] px-1 rounded">code</code>,{' '}
          <code className="text-xs bg-[var(--color-primary-bg)] text-[var(--color-primary)] px-1 rounded">website</code>,{' '}
          <code className="text-xs bg-[var(--color-primary-bg)] text-[var(--color-primary)] px-1 rounded">is_active</code>.
        </p>

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
              Arraste um arquivo CSV ou XLSX ou{' '}
              <span className="text-[var(--color-primary)] underline">clique para selecionar</span>
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

        {/* Job progress */}
        {job && (
          <div className="bg-[var(--color-card-bg)] border border-[var(--color-border)] rounded-xl p-4 space-y-3">
            <div className="flex items-center gap-2">
              {isActive && <Loader2 size={16} className="animate-spin text-[var(--color-primary)]" />}
              {isDone && <CheckCircle size={16} className="text-[var(--color-success)]" />}
              {isFailed && <XCircle size={16} className="text-[var(--color-error)]" />}
              <span className="text-sm font-medium text-[var(--color-text)]">
                {isActive ? 'Processando...' : isDone ? 'Concluído' : 'Falhou'}
              </span>
            </div>
            <div className="w-full bg-[var(--color-border)] rounded-full h-2 overflow-hidden">
              <div
                className="h-2 rounded-full bg-[var(--color-primary)] transition-all duration-300"
                style={{ width: `${job.progress_pct}%` }}
              />
            </div>
            <div className="flex gap-4 text-sm text-[var(--color-text-muted)]">
              <span><strong className="text-[var(--color-text)]">{job.processed_rows}</strong>/{job.total_rows} linhas</span>
              <span className="text-[var(--color-success)]"><strong>{job.created_count}</strong> criados/atualizados</span>
              {job.error_count > 0 && (
                <span className="text-[var(--color-error)]"><strong>{job.error_count}</strong> erros</span>
              )}
            </div>
            {(job.errors ?? []).length > 0 && (
              <details className="text-xs">
                <summary className="cursor-pointer text-[var(--color-error)] font-medium">
                  Ver erros ({job.errors.length})
                </summary>
                <div className="mt-2 max-h-40 overflow-y-auto border border-[var(--color-border)] rounded-lg divide-y divide-[var(--color-border)]">
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
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={handleUpload}
            disabled={!file || uploading || isActive}
            className={clsx(
              'flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-medium text-white transition-colors',
              file && !uploading && !isActive
                ? 'bg-[var(--color-primary)] hover:bg-[var(--color-primary-dark)]'
                : 'bg-[var(--color-border)] cursor-not-allowed text-[var(--color-text-muted)]',
            )}
          >
            {uploading || isActive ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
            {uploading || isActive ? 'Enviando...' : 'Importar'}
          </button>
          <button
            onClick={handleDownloadTemplate}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border border-[var(--color-border)] hover:bg-[var(--color-body-bg)] transition-colors text-[var(--color-text)]"
          >
            <Download size={16} />
            Baixar template CSV
          </button>
        </div>
      </div>
    </Modal>
  );
}
