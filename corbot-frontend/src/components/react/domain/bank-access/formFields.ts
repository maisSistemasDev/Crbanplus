import type { FormFieldDef } from '../../../../lib/api/types';

export function isCorbanRole(role: string | undefined): boolean {
  return role === 'empresa_admin';
}

export function buildBankAccessFormFields(
  fields: FormFieldDef[],
  opts: { isEdit: boolean; hideUser?: boolean; targetUserRole?: string },
): FormFieldDef[] {
  const corban = isCorbanRole(opts.targetUserRole);

  return fields
    .filter((f) => {
      if (opts.hideUser && f.name === 'user') return false;
      if (opts.isEdit && (f.name === 'bank' || f.name === 'user')) return false;
      if (corban && f.name === 'is_master') return false;
      return true;
    })
    .map((f) => {
      if (f.name === 'password' && opts.isEdit) {
        return { ...f, required: false, label: 'Senha (deixe em branco para manter)' };
      }
      return f;
    });
}

export function defaultBankAccessValues(targetUserRole?: string): Record<string, unknown> {
  return {
    is_active: true,
    is_master: isCorbanRole(targetUserRole),
  };
}
