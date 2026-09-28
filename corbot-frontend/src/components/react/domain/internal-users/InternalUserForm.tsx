import { useState, useEffect } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import type { InternalUser, InternalUserFormData, PermissionGroup } from '../../../../lib/api/types/internal-users';
import { DynamicForm } from '../../forms/DynamicForm';
import type { FormFieldDef } from '../../../../lib/api/types';
import toast from 'react-hot-toast';
import { PageHeader } from '../../ui/PageHeader';
import { COLABORADORES_ROUTES } from '../../../../lib/routes/colaboradores';

interface InternalUserFormProps {
  userId?: number;
  initialData?: InternalUser;
  onSuccess?: () => void;
}

export default function InternalUserForm({ userId, initialData, onSuccess }: InternalUserFormProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fields, setFields] = useState<FormFieldDef[]>([]);
  const [initialValues, setInitialValues] = useState<Record<string, unknown> | undefined>(
    initialData as Record<string, unknown> | undefined,
  );
  const [fieldsLoading, setFieldsLoading] = useState(true);
  const [permissionGroups, setPermissionGroups] = useState<PermissionGroup[]>([]);
  const [selectedPermissions, setSelectedPermissions] = useState<Set<string>>(new Set());
  const [role, setRole] = useState<'admin' | 'colaborador' | ''>('');

  useEffect(() => {
    const loadFields = async () => {
      setFieldsLoading(true);
      setInitialValues(initialData as Record<string, unknown> | undefined);
      try {
        const [formFields, userData, available] = await Promise.all([
          api.get<FormFieldDef[]>(ENDPOINTS.INTERNAL_USER_FORM_FIELDS),
          userId
            ? api.get<InternalUser>(ENDPOINTS.INTERNAL_USER_DETAIL(userId))
            : Promise.resolve(null),
          api.get<PermissionGroup[]>(ENDPOINTS.AVAILABLE_PERMISSIONS),
        ]);
        setFields(Array.isArray(formFields) ? formFields : []);
        setPermissionGroups(Array.isArray(available) ? available : []);
        if (userData) {
          setInitialValues(userData as unknown as Record<string, unknown>);
          setRole(userData.role);
          setSelectedPermissions(new Set((userData.permissions || []).map((p) => p.codename)));
        }
      } catch (err) {
        setError(extractErrorMessage(err));
      } finally {
        setFieldsLoading(false);
      }
    };
    loadFields();
  }, [userId, initialData]);

  const handleFormChange = (name: string, value: unknown) => {
    if (name === 'role') {
      setRole(value as 'admin' | 'colaborador');
      if (value === 'admin') {
        setSelectedPermissions(new Set());
      }
    }
  };

  const togglePermission = (codename: string) => {
    setSelectedPermissions((prev) => {
      const next = new Set(prev);
      if (next.has(codename)) next.delete(codename);
      else next.add(codename);
      return next;
    });
  };

  const handleSubmit = async (data: InternalUserFormData) => {
    setLoading(true);
    setError(null);

    const payload: InternalUserFormData = {
      ...data,
      permission_ids: role === 'colaborador' ? [...selectedPermissions] : [],
    };

    try {
      if (userId) {
        const response = await api.put<{ message: string; user: InternalUser }>(
          ENDPOINTS.INTERNAL_USER_DETAIL(userId),
          payload,
        );
        toast.success(response.message || 'Usuário atualizado com sucesso.');
      } else {
        const response = await api.post<{ message: string; user: InternalUser }>(
          ENDPOINTS.INTERNAL_USERS,
          payload,
        );
        toast.success(response.message || 'Usuário criado com sucesso.');
      }

      if (onSuccess) {
        onSuccess();
      } else {
        window.location.href = COLABORADORES_ROUTES.list;
      }
    } catch (err) {
      const msg = extractErrorMessage(err);
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <PageHeader
        title={userId ? 'Editar colaborador' : 'Novo colaborador'}
        subtitle="Vinculado apenas à promotora — não selecione nem associe corban"
      />

      <p className="mb-3 text-xs text-gray-500">
        Colaboradores e administradores da promotora não pertencem a nenhum corban.
        O acesso é controlado por papel e, para colaboradores, pelas permissões granulares.
      </p>

      {error && (
        <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      )}

      <div className="card space-y-6">
        {fieldsLoading ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin h-6 w-6 border-2 border-[var(--color-primary)] border-t-transparent rounded-full" />
          </div>
        ) : (
          <>
            <DynamicForm
              fields={fields}
              onSubmit={handleSubmit}
              onChange={handleFormChange}
              initialValues={initialValues}
              loading={loading}
              submitLabel={userId ? 'Atualizar' : 'Criar'}
            />

            {role === 'colaborador' && (
              <div className="border-t border-gray-200 pt-6">
                <h3 className="text-base font-semibold text-gray-900 mb-1">Permissões granulares</h3>
                <p className="text-xs text-gray-500 mb-4">
                  Selecione o que este colaborador pode fazer no sistema.
                </p>

                {permissionGroups.length === 0 ? (
                  <p className="text-sm text-gray-500">Carregando permissões...</p>
                ) : (
                  <div className="space-y-5">
                    {permissionGroups.map((group) => (
                      <div key={group.category}>
                        <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2">
                          {group.label}
                        </h4>
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                          {group.permissions.map((perm) => (
                            <label
                              key={perm.codename}
                              className="flex items-start gap-2 p-2 rounded-lg border border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors"
                            >
                              <input
                                type="checkbox"
                                checked={selectedPermissions.has(perm.codename)}
                                onChange={() => togglePermission(perm.codename)}
                                className="mt-0.5 h-4 w-4 rounded border-gray-300 text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
                              />
                              <span className="text-sm text-gray-700 leading-tight">{perm.name}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
