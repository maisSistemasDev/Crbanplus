import { useState, useEffect } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { Button } from '../../ui/Button';
import { Select } from '../../ui/Select';
import { FileUpload } from '../../ui/FileUpload';
import { PageSpinner } from '../../ui/Spinner';
import type { Layout } from '../../../../lib/api/types';
import { ArrowLeft, Upload } from 'lucide-react';
import toast from 'react-hot-toast';

export function BatchUpload() {
  const [layouts, setLayouts] = useState<Layout[]>([]);
  const [selectedLayout, setSelectedLayout] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const res = await api.get<Layout[] | { results: Layout[] }>(ENDPOINTS.LAYOUTS);
        const list = Array.isArray(res) ? res : res.results || [];
        setLayouts(list);
      } catch {
        toast.error('Erro ao carregar layouts');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function handleUpload() {
    if (!selectedLayout || !file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('layout_id', selectedLayout);
      const result = await api.upload(ENDPOINTS.BATCHES, formData);
      toast.success('Lote enviado com sucesso!');

      // Extract batchId from serialized response (which now includes id field)
      const batchId = (result as any)?.id;
      if (!batchId) {
        toast.error('Erro: ID do lote não retornado');
        return;
      }

      // Redirect directly to batch detail page with ValueMatcher
      window.location.href = `${window.location.origin}/proposals/batches/${batchId}`;
    } catch {
      toast.error('Erro ao enviar lote');
    } finally {
      setUploading(false);
    }
  }

  if (loading) return <PageSpinner />;

  return (
    <div className="animate-fadeIn">
      <div className="flex items-center gap-3 mb-6">
        <Button variant="ghost" size="sm" onClick={() => (window.location.href = `${window.location.origin}/proposals/batches`)}>
          <ArrowLeft size={16} />
        </Button>
        <h1 className="text-2xl font-bold text-gray-900">Enviar Lote de Propostas</h1>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 max-w-xl transition-all duration-300">
        <div className="space-y-4">
          <Select
            label="Layout de Importacao"
            required
            options={layouts.map((l) => ({ value: l.id, label: `${l.name} (${l.bank_name})` }))}
            value={selectedLayout}
            onChange={(e) => setSelectedLayout(e.target.value)}
          />

          <FileUpload
            label="Arquivo de Propostas"
            accept=".xlsx,.xls,.csv"
            onFileSelect={setFile}
          />

          <div className="pt-4">
            <Button
              onClick={handleUpload}
              loading={uploading}
              disabled={!selectedLayout || !file}
            >
              <Upload size={16} />
              Enviar Lote
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
