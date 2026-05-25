import { useCallback, useState } from 'react';
import clsx from 'clsx';
import { Upload, X, FileSpreadsheet } from 'lucide-react';

interface FileUploadProps {
  label?: string;
  accept?: string;
  onFileSelect: (file: File) => void;
  error?: string;
  className?: string;
}

export function FileUpload({ label, accept, onFileSelect, error, className }: FileUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) {
        setSelectedFile(file);
        onFileSelect(file);
      }
    },
    [onFileSelect],
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        setSelectedFile(file);
        onFileSelect(file);
      }
    },
    [onFileSelect],
  );

  function clearFile() {
    setSelectedFile(null);
  }

  return (
    <div className={clsx('w-full', className)}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      )}
      {selectedFile ? (
        <div className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg bg-gray-50">
          <FileSpreadsheet size={20} className="text-green-600 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-700 truncate">{selectedFile.name}</p>
            <p className="text-xs text-gray-500">
              {(selectedFile.size / 1024).toFixed(1)} KB
            </p>
          </div>
          <button onClick={clearFile} className="p-1 hover:bg-gray-200 rounded" type="button">
            <X size={16} className="text-gray-500" />
          </button>
        </div>
      ) : (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={clsx(
            'border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer',
            dragOver ? 'border-[var(--color-primary)] bg-[var(--color-primary-bg)]' : 'border-gray-300 hover:border-gray-400',
          )}
        >
          <input
            type="file"
            accept={accept}
            onChange={handleChange}
            className="hidden"
            id="file-upload"
          />
          <label htmlFor="file-upload" className="cursor-pointer">
            <Upload size={24} className="mx-auto text-gray-400 mb-2" />
            <p className="text-sm text-gray-600">
              Arraste um arquivo ou <span className="text-[var(--color-primary)] font-medium">clique para selecionar</span>
            </p>
            {accept && (
              <p className="text-xs text-gray-400 mt-1">Formatos aceitos: {accept}</p>
            )}
          </label>
        </div>
      )}
      {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
    </div>
  );
}
