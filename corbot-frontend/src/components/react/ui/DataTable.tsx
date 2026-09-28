import { useState, useMemo } from 'react';
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import clsx from 'clsx';
import { Pagination } from './Pagination';
import { PageSpinner, EmptyState } from './Spinner';

export interface Column<T> {
  key: string;
  header: string;
  render?: (item: T) => React.ReactNode;
  sortable?: boolean;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  loading?: boolean;
  totalItems?: number;
  currentPage?: number;
  pageSize?: number;
  onPageChange?: (page: number) => void;
  onRowClick?: (item: T) => void;
  emptyMessage?: string;
  keyExtractor?: (item: T) => string | number;
  selectable?: boolean;
  selectedKeys?: Set<string>;
  onSelectionChange?: (keys: Set<string>) => void;
  /** Coluna extra de ações no fim da linha (ex.: botão de editar). */
  rowActions?: (item: T) => React.ReactNode;
  compact?: boolean;
}

type SortDir = 'asc' | 'desc' | null;

export function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  loading = false,
  totalItems,
  currentPage = 1,
  pageSize = 10,
  onPageChange,
  onRowClick,
  emptyMessage = 'Nenhum item encontrado',
  keyExtractor,
  selectable = false,
  selectedKeys,
  onSelectionChange,
  rowActions,
  compact = false,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>(null);

  function handleSort(key: string) {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : sortDir === 'desc' ? null : 'asc');
      if (sortDir === 'desc') setSortKey(null);
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  }

  function getKey(item: T, idx: number): string {
    return String(keyExtractor ? keyExtractor(item) : idx);
  }

  function toggleAll() {
    if (!onSelectionChange) return;
    const allKeys = new Set(sortedData.map((item, idx) => getKey(item, idx)));
    const allSelected = allKeys.size > 0 && [...allKeys].every((k) => selectedKeys?.has(k));
    if (allSelected) {
      onSelectionChange(new Set());
    } else {
      onSelectionChange(allKeys);
    }
  }

  function toggleOne(key: string) {
    if (!onSelectionChange || !selectedKeys) return;
    const next = new Set(selectedKeys);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    onSelectionChange(next);
  }

  const sortedData = useMemo(() => {
    if (!sortKey || !sortDir) return data;
    return [...data].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      const cmp = String(aVal).localeCompare(String(bVal), 'pt-BR', { numeric: true });
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [data, sortKey, sortDir]);

  const allSelected =
    selectable &&
    sortedData.length > 0 &&
    sortedData.every((item, idx) => selectedKeys?.has(getKey(item, idx)));
  const someSelected =
    selectable && !!selectedKeys && selectedKeys.size > 0 && !allSelected;


  const totalPages = totalItems ? Math.ceil(totalItems / pageSize) : 1;

  if (loading) return <PageSpinner />;
  if (data.length === 0) return <EmptyState title={emptyMessage} />;

  const cellPad = compact ? 'px-2 py-1' : 'px-3 py-2';

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden">
      <div className="overflow-x-auto">
        <table className={clsx('w-full', compact ? 'text-[11px] leading-tight' : 'text-sm')}>
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50/50">
              {selectable && (
                <th className={clsx(cellPad, 'w-8')}>
                  <input
                    type="checkbox"
                    checked={allSelected}
                    ref={(el) => { if (el) el.indeterminate = someSelected; }}
                    onChange={toggleAll}
                    className="rounded border-gray-300 text-[var(--color-primary)] cursor-pointer"
                  />
                </th>
              )}
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={clsx(
                    cellPad,
                    compact ? 'text-[10px]' : 'text-[11px]',
                    'text-left font-medium text-gray-500 uppercase tracking-wider',
                    col.sortable && 'cursor-pointer select-none hover:text-gray-700',
                    col.className,
                  )}
                  onClick={() => col.sortable && handleSort(col.key)}
                >
                  <span className="flex items-center gap-1">
                    {col.header}
                    {col.sortable && (
                      sortKey === col.key ? (
                        sortDir === 'asc' ? <ArrowUp size={14} /> : <ArrowDown size={14} />
                      ) : (
                        <ArrowUpDown size={14} className="opacity-30" />
                      )
                    )}
                  </span>
                </th>
              ))}
              {rowActions && (
                <th className={clsx(cellPad, 'w-1 text-right text-[10px] font-medium text-gray-500 uppercase tracking-wider')}>
                  Ações
                </th>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {sortedData.map((item, idx) => {
              const key = getKey(item, idx);
              const isSelected = selectable && !!selectedKeys?.has(key);
              return (
                <tr
                  key={key}
                  className={clsx(
                    'transition-colors',
                    onRowClick && !selectable && 'cursor-pointer hover:bg-gray-50',
                    isSelected ? 'bg-blue-50' : 'hover:bg-gray-50',
                  )}
                  onClick={() => {
                    if (selectable) toggleOne(key);
                    else onRowClick?.(item);
                  }}
                >
                  {selectable && (
                    <td className={clsx(cellPad, 'w-8')} onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleOne(key)}
                        className="rounded border-gray-300 text-[var(--color-primary)] cursor-pointer"
                      />
                    </td>
                  )}
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={clsx(cellPad, 'text-gray-700', col.className)}
                      onClick={() => !selectable && onRowClick?.(item)}
                    >
                      {col.render
                        ? col.render(item)
                        : (item[col.key] as React.ReactNode) ?? '-'}
                    </td>
                  ))}
                  {rowActions && (
                    <td
                      className={clsx(cellPad, 'text-right whitespace-nowrap')}
                      onClick={(e) => e.stopPropagation()}
                    >
                      {rowActions(item)}
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {onPageChange && totalItems && (
        <div className="border-t border-gray-100 px-4">
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={onPageChange}
            totalItems={totalItems}
            pageSize={pageSize}
          />
        </div>
      )}
    </div>
  );
}
