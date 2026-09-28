import { useState, useEffect } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { DynamicForm } from '../../forms/DynamicForm';
import { Button } from '../../ui/Button';
import { InactivationButton } from '../../ui/InactivationButton';
import type { FormFieldDef, Company } from '../../../../lib/api/types';
import { PageSpinner } from '../../ui/Spinner';
import { ArrowLeft } from 'lucide-react';
import toast from 'react-hot-toast';

interface CompanyFormProps {
  companyId?: string;
}

export function CompanyForm({ companyId }: CompanyFormProps) {
  const [fields, setFields] = useState<FormFieldDef[]>([]);
  const [initialValues, setInitialValues] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const isEdit = !!companyId;

  useEffect(() => {
    async function load() {
      try {
        const [formFields, companyData] = await Promise.all([
          api.get<FormFieldDef[]>(ENDPOINTS.FORM_FIELDS_COMPANIES),
          isEdit ? api.get<Company>(ENDPOINTS.COMPANY_DETAIL(companyId!)) : Promise.resolve(null),
        ]);
        
        let allFields = Array.isArray(formFields) ? formFields : [];
        
        // Se não está editando, adicionar campos do usuário admin
        if (!isEdit) {
          const adminUserFields: FormFieldDef[] = [
            {
              name: 'admin_cpf',
              type: 'text',
              label: 'CPF do Administrador',
              required: true,
              mask: '999.999.999-99',

            },
            { 
              name: 'admin_password', 
              type: 'password', 
              label: 'Senha do Admin', 
              required: true,
            },
            { 
              name: 'admin_matricula', 
              type: 'text', 
              label: 'Matrícula', 
              required: false,
            },
            { 
              name: 'admin_certificado', 
              type: 'text', 
              label: 'Certificado', 
              required: false,
            },
          ];
          allFields = [...allFields, ...adminUserFields];
        }
        
        setFields(allFields);
        if (companyData) {
          setInitialValues(companyData as unknown as Record<string, any>);
        }
      } catch (error) {
        toast.error(extractErrorMessage(error));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [companyId]);

  async function handleSubmit(values: Record<string, any>) {
    setSaving(true);
    try {
      if (isEdit) {
        // Modo de edição - envia apenas dados da empresa
        const hasFiles = Object.values(values).some((v) => v instanceof File);
        if (hasFiles) {
          const formData = new FormData();
          Object.entries(values).forEach(([key, val]) => {
            if (val !== null && val !== undefined) {
              formData.append(key, val instanceof File ? val : String(val));
            }
          });
          await api.upload(ENDPOINTS.COMPANY_DETAIL(companyId!), formData, 'PATCH');
        } else {
          await api.patch(ENDPOINTS.COMPANY_DETAIL(companyId!), values);
        }
        toast.success('Corban atualizado!');
      } else {
        // Modo de criação - separar dados da empresa e do usuário admin
        const companyData: Record<string, any> = {};
        const adminUserData: Record<string, any> = {};
        
        Object.entries(values).forEach(([key, val]) => {
          if (key.startsWith('admin_')) {
            // Remover o prefixo 'admin_' e adicionar ao objeto adminUserData
            const cleanKey = key.replace('admin_', '');
            adminUserData[cleanKey] = val;
          } else if (key !== 'admin_user_separator') {
            companyData[key] = val;
          }
        });
        
        // Preparar payload
        const payload = {
          company: companyData,
          admin_user: adminUserData,
        };
        
        // Verificar se há arquivos (logo)
        const hasFiles = Object.values(companyData).some((v) => v instanceof File);
        
        if (hasFiles) {
          const formData = new FormData();
          // Adicionar dados da empresa
          Object.entries(companyData).forEach(([key, val]) => {
            if (val !== null && val !== undefined) {
              formData.append(`company.${key}`, val instanceof File ? val : String(val));
            }
          });
          // Adicionar dados do usuário admin
          Object.entries(adminUserData).forEach(([key, val]) => {
            if (val !== null && val !== undefined) {
              formData.append(`admin_user.${key}`, String(val));
            }
          });
          await api.upload(ENDPOINTS.COMPANIES, formData);
        } else {
          await api.post(ENDPOINTS.COMPANIES, payload);
        }
        
        toast.success('Corban criado!');
        window.location.href = `${window.location.origin}/companies`;
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
        <a href="/companies">
          <Button variant="ghost" size="sm">
            <ArrowLeft size={16} />
          </Button>
        </a>
        <h1 className="page-title flex-1">
          {isEdit ? 'Editar corban' : 'Novo corban'}
        </h1>
        {isEdit && companyId && (
          <InactivationButton
            isActive={Boolean(initialValues.is_active)}
            activationUrl={ENDPOINTS.COMPANY_ACTIVATION(companyId)}
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
