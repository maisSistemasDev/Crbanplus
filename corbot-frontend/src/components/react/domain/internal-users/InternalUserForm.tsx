import { useState } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import type { InternalUser, InternalUserFormData } from '../../../../lib/api/types/internal-users';
import { DynamicForm } from '../../forms/DynamicForm';
import type { FormFieldDef } from '../../../../lib/api/types';

interface InternalUserFormProps {
  userId?: number;
  initialData?: InternalUser;
  onSuccess?: () => void;
}

export default function InternalUserForm({ userId, initialData, onSuccess }: InternalUserFormProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fields, setFields] = useState<FormFieldDef[]>([]);

  // Carregar campos do formulário
  useState(() => {
    const loadFields = async () => {
      try {
        const response = await api.get<FormFieldDef[]>(ENDPOINTS.INTERNAL_USER_FORM_FIELDS);
        setFields(response);
      } catch (err) {
        console.error('Erro ao carregar campos do formulário:', err);
        setError('Erro ao carregar formulário');
      }
    };
    loadFields();
  });

  const handleSubmit = async (data: InternalUserFormData) => {
    setLoading(true);
    setError(null);

    try {
      if (userId) {
        // Atualizar usuário existente
        const response = await api.put<{ message: string; user: InternalUser }>(
          ENDPOINTS.INTERNAL_USER_DETAIL(userId),
          data
        );
        alert(response.message || 'Usuário atualizado com sucesso!');
      } else {
        // Criar novo usuário
        const response = await api.post<{ message: string; user: InternalUser }>(
          ENDPOINTS.INTERNAL_USERS,
          data
        );
        alert(response.message || 'Usuário criado com sucesso!');
      }

      if (onSuccess) {
        onSuccess();
      } else {
        window.location.href = '/internal-users';
      }
    } catch (err: any) {
      console.error('Erro ao salvar usuário:', err);
      setError(err.response?.data?.detail || 'Erro ao salvar usuário');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          {userId ? 'Editar Usuário Interno' : 'Novo Usuário Interno'}
        </h1>
        <p className="text-gray-600 mt-2">
          Gerencie usuários da promotora (Administradores e Colaboradores)
        </p>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      <div className="bg-white rounded-lg shadow-md p-6">
        <DynamicForm
          fields={fields}
          onSubmit={handleSubmit}
          initialData={initialData}
          submitLabel={userId ? 'Atualizar' : 'Criar'}
          isLoading={loading}
        />
      </div>
    </div>
  );
}
