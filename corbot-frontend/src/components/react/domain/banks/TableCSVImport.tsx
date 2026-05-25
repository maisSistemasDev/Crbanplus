import { useState, useEffect } from 'react';
import { Modal } from '../../ui/Modal';
import { Button } from '../../ui/Button';
import { FileUpload } from '../../ui/FileUpload';
import { Select } from '../../ui/Select';
import { api, API_URL } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { Download, Upload, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import toast from 'react-hot-toast';

interface Bank {
  id: string;
  name: string;
}

interface CSVImportResult {
  created_count: number;
  updated_count: number;
  created_tables: Array<{ name: string; bank: string; agreement: string; action: string }>;
  updated_tables: Array<{ name: string; bank: string; agreement: string; action: string }>;
  errors_count: number;
  errors: string[];
  detail: string;
}

interface TableCSVImportProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function TableCSVImport({ isOpen, onClose, onSuccess }: TableCSVImportProps) {
  const [selectedBankId, setSelectedBankId] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<CSVImportResult | null>(null);

  useEffect(() => {
    if (!isOpen) {
      // Reset ao fechar
      setSelectedBankId('');
      setFile(null);
      setResult(null);
    }
  }, [isOpen]);

  async function handleDownloadTemplate() {
    try {
      const tokens = localStorage.getItem('tokens');
      const accessToken = tokens ? JSON.parse(tokens).access : '';
      
      const response = await fetch(`${API_URL}${ENDPOINTS.TABLES_EXPORT_CSV}`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });
      
      if (!response.ok) throw new Error('Erro ao baixar template');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'template_tabelas.csv';
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success('Template baixado com sucesso!');
    } catch (error) {
      toast.error('Erro ao baixar template');
    }
  }

  async function handleUpload() {
    if (!selectedBankId) {
      toast.error('Selecione um banco');
      return;
    }
    
    if (!file) {
      toast.error('Selecione um arquivo');
      return;
    }

    setUploading(true);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('bank_id', selectedBankId);

      const response = await api.post<CSVImportResult>(
        ENDPOINTS.TABLES_CREATE_BATCH,
        formData
      );

      setResult(response);
      
      if (response.errors_count === 0) {
        toast.success(response.detail || 'Importação concluída!');
        onSuccess();
      } else if (response.created_count > 0 || response.updated_count > 0) {
        toast.success(`Importação parcial: ${response.created_count} criadas, ${response.updated_count} atualizadas`);
        onSuccess();
      } else {
        toast.error('Nenhuma tabela foi criada/atualizada');
      }
    } catch (error: any) {
      toast.error(error.message || 'Erro ao importar arquivo');
      setResult(null);
    } finally {
      setUploading(false);
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Importar Tabelas via CSV">
      <div className="space-y-4">
        {/* Instruções */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <h4 className="text-sm font-medium text-blue-900 mb-1">📋 Instruções</h4>
          <ol className="text-xs text-blue-800 space-y-1 list-decimal list-inside">
            <li>Baixe o template CSV clicando no botão abaixo</li>
            <li>Preencha os dados das tabelas no formato correto</li>
            <li>Selecione o banco e faça upload do arquivo</li>
            <li>Tabelas existentes serão atualizadas automaticamente</li>
          </ol>
        </div>

        {/* Botão Download Template */}
        <Button
          variant="secondary"
          onClick={handleDownloadTemplate}
          className="w-full"
        >
          <Download size={16} />
          Baixar Template CSV
        </Button>

        {/* Select de Banco */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Banco <span className="text-red-500">*</span>
          </label>
          <Select
            value={selectedBankId}
            onChange={(e) => setSelectedBankId(e.target.value)}
            options_url={ENDPOINTS.BANKS}
            placeholder="Selecione um banco"
          />
        </div>

        {/* Upload de Arquivo */}
        <FileUpload
          label="Arquivo CSV"
          accept=".csv"
          onFileSelect={setFile}
        />

        {/* Resultado */}
        {result && (
          <div className="space-y-2 border-t pt-4">
            <div className="flex items-start gap-2 p-3 rounded-lg bg-gray-50">
              <Clock size={18} className="text-gray-600 mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900">Resultado da Importação</p>
                <div className="text-xs text-gray-600 mt-1 space-y-1">
                  {result.created_count > 0 && (
                    <div className="flex items-center gap-1">
                      <CheckCircle size={14} className="text-green-600" />
                      <span>{result.created_count} tabela(s) criada(s)</span>
                    </div>
                  )}
                  {result.updated_count > 0 && (
                    <div className="flex items-center gap-1">
                      <CheckCircle size={14} className="text-blue-600" />
                      <span>{result.updated_count} tabela(s) atualizada(s)</span>
                    </div>
                  )}
                  {result.errors_count > 0 && (
                    <div className="flex items-center gap-1">
                      <AlertCircle size={14} className="text-red-600" />
                      <span>{result.errors_count} erro(s)</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {result.errors && result.errors.length > 0 && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 max-h-40 overflow-y-auto">
                <h4 className="text-xs font-medium text-red-900 mb-2">Erros:</h4>
                <ul className="text-xs text-red-800 space-y-1">
                  {result.errors.map((error, idx) => (
                    <li key={idx} className="flex items-start gap-1">
                      <span className="text-red-500 shrink-0">•</span>
                      <span>{error}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Botões de Ação */}
        <div className="flex gap-2 pt-2">
          <Button variant="secondary" onClick={onClose} className="flex-1">
            Fechar
          </Button>
          <Button
            onClick={handleUpload}
            disabled={!selectedBankId || !file || uploading}
            loading={uploading}
            className="flex-1"
          >
            <Upload size={16} />
            {uploading ? 'Importando...' : 'Importar'}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
