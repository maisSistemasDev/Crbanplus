import { useState, useEffect } from 'react';
import { useStore } from '@nanostores/react';
import { $currentUser } from '../../../../lib/stores/auth';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { DynamicForm } from '../../forms/DynamicForm';
import { Button } from '../../ui/Button';
import { InactivationButton } from '../../ui/InactivationButton';
import type { FormFieldDef, User, ExtraData } from '../../../../lib/api/types';
import { PageSpinner } from '../../ui/Spinner';
import { ArrowLeft } from 'lucide-react';
import toast from 'react-hot-toast';

interface UserFormProps {
  userId?: number;
}

const EXTRA_DATA_FIELDS: (keyof ExtraData)[] = [
  'pix_key',
  'pix_type',
  'phone',
  'birth_date',
  'rg',
  'rg_emission_date',
  'rg_emission_organ',
];

/** Achata extra_data nos campos que o DynamicForm espera no root. */
function flattenUserForForm(user: User): Record<string, unknown> {
  const extra = user.extra_data ?? {};
  return {
    ...user,
    ...Object.fromEntries(
      EXTRA_DATA_FIELDS.map((field) => [field, (extra as ExtraData)[field] ?? '']),
    ),
  };
}

/** Monta payload PATCH com extra_data aninhado (como a API espera). */
function buildUserPayload(values: Record<string, unknown>): Record<string, unknown> {
  const extra_data: Record<string, unknown> = {};
  for (const field of EXTRA_DATA_FIELDS) {
    if (values[field] !== undefined && values[field] !== '') {
      extra_data[field] = values[field];
    }
  }

  const payload = { ...values };
  for (const field of EXTRA_DATA_FIELDS) {
    delete payload[field];
  }
  delete payload.extra_data;

  if (Object.keys(extra_data).length > 0) {
    payload.extra_data = extra_data;
  }
  return payload;
}

export function UserForm({ userId }: UserFormProps) {
  const currentUser = useStore($currentUser);
  const canInactivate = currentUser?.role !== 'gerente_comercial';
  const [fields, setFields] = useState<FormFieldDef[]>([]);
  const [initialValues, setInitialValues] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const isEdit = !!userId;

  useEffect(() => {
    async function load() {
      try {
        const fieldsEndpoint = isEdit ? ENDPOINTS.FORM_FIELDS_USERS : ENDPOINTS.FORM_FIELDS_USERS_CREATE;
        const [formFields, userData] = await Promise.all([
          api.get<FormFieldDef[]>(fieldsEndpoint),
          isEdit ? api.get<User>(ENDPOINTS.USER_DETAIL(userId!)) : Promise.resolve(null),
        ]);
        setFields(Array.isArray(formFields) ? formFields : []);
        if (userData) {
          setInitialValues(flattenUserForForm(userData));
        }
      } catch (error) {
        toast.error(extractErrorMessage(error));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [userId]);

  async function handleSubmit(values: Record<string, any>) {
    setSaving(true);
    try {
      const payload = buildUserPayload(values);
      if (isEdit) {
        await api.patch(ENDPOINTS.USER_DETAIL(userId!), payload);
        toast.success('Usuario atualizado com sucesso!');
      } else {
        await api.post(ENDPOINTS.USERS, buildUserPayload(values));
        toast.success('Usuario criado com sucesso!');
        window.location.href = `${window.location.origin}/users`;
      }
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <PageSpinner />;

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <a href="/users">
          <Button variant="ghost" size="sm">
            <ArrowLeft size={16} />
          </Button>
        </a>
        <h1 className="page-title flex-1">
          {isEdit ? 'Editar usuário' : 'Novo usuário'}
        </h1>
        {isEdit && userId && canInactivate && (
          <InactivationButton
            isActive={Boolean(initialValues.is_active)}
            activationUrl={ENDPOINTS.USER_ACTIVATION(userId)}
            inactivatedAt={initialValues.inactivated_at as string | undefined}
            inactivationReason={initialValues.inactivation_reason as string | undefined}
            onDone={() => window.location.reload()}
          />
        )}
      </div>
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <DynamicForm
          fields={fields}
          initialValues={initialValues}
          onSubmit={handleSubmit}
          loading={saving}
          submitLabel={isEdit ? 'Atualizar' : 'Criar'}
        />
      </div>
    </div>
  );
}
