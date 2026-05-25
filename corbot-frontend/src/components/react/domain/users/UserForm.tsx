import { useState, useEffect } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { DynamicForm } from '../../forms/DynamicForm';
import { Button } from '../../ui/Button';
import type { FormFieldDef, User } from '../../../../lib/api/types';
import { PageSpinner } from '../../ui/Spinner';
import { ArrowLeft } from 'lucide-react';
import toast from 'react-hot-toast';

interface UserFormProps {
  userId?: number;
}

export function UserForm({ userId }: UserFormProps) {
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
          setInitialValues(userData as unknown as Record<string, any>);
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
      if (isEdit) {
        await api.patch(ENDPOINTS.USER_DETAIL(userId!), values);
        toast.success('Usuario atualizado com sucesso!');
      } else {
        await api.post(ENDPOINTS.USERS, values);
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
      <div className="flex items-center gap-3 mb-6">
        <a href="/users">
          <Button variant="ghost" size="sm">
            <ArrowLeft size={16} />
          </Button>
        </a>
        <h1 className="text-2xl font-bold text-gray-900">
          {isEdit ? 'Editar Usuario' : 'Novo Usuario'}
        </h1>
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
