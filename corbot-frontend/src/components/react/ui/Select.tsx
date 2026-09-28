import { SearchSelect } from './SearchSelect';
import type { SelectOption } from '../../../lib/api/formFieldOptions';

interface SelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'onChange'> {
  label?: string;
  error?: string;
  options?: readonly SelectOption[];
  options_url?: string;
  placeholder?: string;
  searchPlaceholder?: string;
  allowEmpty?: boolean;
  compact?: boolean;
  triggerClassName?: string;
  onChange?: React.ChangeEventHandler<HTMLSelectElement>;
}

/**
 * Todo select do sistema tem busca: este componente delega para o SearchSelect.
 * Mantido como `Select` para não quebrar os pontos que já o importavam.
 */
export function Select({ allowEmpty, ...props }: SelectProps) {
  // Campo obrigatório não oferece a opção vazia; os demais podem ser limpos.
  return <SearchSelect allowEmpty={allowEmpty ?? !props.required} {...props} />;
}
