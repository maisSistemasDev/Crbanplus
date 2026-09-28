from rest_framework.response import Response
from rest_framework import status, permissions
from django.db import transaction
from django.db.utils import IntegrityError
from django.http import HttpResponse

from ..base_views import BaseApiView
from ..models import User, ExtraData, Company, validate_pix_binding
from ..permissions import IsGerente, IsGerenteOrLider, IsAdmin
from ..utils import normalize_cpf


class VendedorImportView(BaseApiView):
    """
    API endpoint para importação em massa de vendedores a partir de um arquivo.
    """
    permission_classes = [IsGerente, IsAdmin]
    
    def post(self, request, format=None):
        """
        Importa vendedores a partir de um arquivo CSV, Excel ou JSON.
        
        O arquivo deve conter as seguintes colunas/campos:
        - cpf (obrigatório): CPF do vendedor
        - email (obrigatório): Email do vendedor
        - first_name (obrigatório): Nome do vendedor
        - last_name: Sobrenome do vendedor
        - password (obrigatório): Senha inicial do vendedor
        - leader_cpf: CPF do líder do vendedor (opcional)
        - company: ID da empresa (opcional)
        - pix_key (obrigatório): Chave PIX do vendedor
        - pix_type (obrigatório): Tipo de chave PIX (cpf, email, telefone, aleatoria)
        
        E pode conter campos opcionais para os dados extras:
        - rg: RG do vendedor
        - rg_emission_date: Data de emissão do RG (formato: DD/MM/AAAA)
        - rg_emission_organ: Órgão emissor do RG
        - birth_date: Data de nascimento (formato: DD/MM/AAAA)
        - phone: Telefone
        """
        # Processa o arquivo enviado
        data, file_path = self.process_file_upload(
            request, 
            supported_types=['.csv', '.xlsx', '.json']
        )
        
        if not data:
            return Response(
                {"detail": "Erro ao processar o arquivo. Verifique se o formato é suportado (CSV, Excel ou JSON)."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Define o mapeamento de tipos
        type_mapping = {
            'birth_date': 'date',
            'rg_emission_date': 'date',
            'pix_key': 'string',
            'phone': 'string',
            'cpf': 'string',
            'email': 'string',
            'first_name': 'string',
            'last_name': 'string',
            'password': 'string',
            'leader_cpf': 'string',
            'company': 'string',
            'pix_type': 'string'
        }
        
        # Converte os tipos de dados
        data = self.convert_data_types(data, type_mapping)
        
        # Valida os dados
        required_fields = ['cpf', 'email', 'first_name', 'password', 'pix_key', 'pix_type']
        valid, errors = self.validate_data(data, required_fields=required_fields)
        
        if not valid:
            return Response(
                {"errors": errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Importa os vendedores
        created_count = 0
        error_count = 0
        error_details = []
        
        for index, item in enumerate(data):
            try:
                with transaction.atomic():
                    # Obtém os dados do vendedor (normaliza CPF para preservar
                    # zeros à esquerda perdidos pelo Excel/pandas).
                    user_data = {
                        'cpf': normalize_cpf(item.get('cpf')),
                        'email': item.get('email'),
                        'first_name': item.get('first_name'),
                        'last_name': item.get('last_name', ''),
                        'role': User.VENDEDOR,
                        'company': item.get('company') or request.user.company
                    }
                    
                    # Trata o líder
                    leader_cpf = item.get('leader_cpf')
                    if leader_cpf:
                        leader_cpf = normalize_cpf(leader_cpf)
                        try:
                            leader = User.objects.get(cpf=leader_cpf, role=User.LIDER)
                            user_data['leader'] = leader
                        except User.DoesNotExist:
                            raise ValueError(f"Líder com CPF {leader_cpf} não encontrado.")
                    
                    # Cria o usuário
                    password = item.get('password')
                    user = User.objects.create_user(**user_data)
                    user.set_password(password)
                    user.save()
                    
                    # Cria os dados extras, com PIX obrigatório
                    extra_fields = [
                        'rg', 'rg_emission_date', 'rg_emission_organ', 
                        'birth_date', 'phone', 'pix_key', 'pix_type'
                    ]
                    
                    extra_data = {k: item.get(k) for k in extra_fields if item.get(k) is not None}
                    
                    # Verificação adicional para garantir que os campos de PIX estejam presentes
                    if 'pix_key' not in extra_data or 'pix_type' not in extra_data:
                        raise ValueError("Os campos 'pix_key' e 'pix_type' são obrigatórios")

                    pix_error = validate_pix_binding(
                        pix_type=extra_data.get('pix_type'),
                        pix_key=extra_data.get('pix_key'),
                        cpf=user.cpf,
                        cnpj=user.company.document if user.company else None,
                    )
                    if pix_error:
                        raise ValueError(pix_error)
                    
                    ExtraData.objects.create(user=user, **extra_data)
                    
                    created_count += 1
                    
            except IntegrityError as e:
                error_count += 1
                error_details.append({
                    'linha': index + 1, 
                    'cpf': item.get('cpf'),
                    'erro': 'CPF ou email já existente no sistema.'
                })
            except ValueError as e:
                error_count += 1
                error_details.append({
                    'linha': index + 1, 
                    'cpf': item.get('cpf'),
                    'erro': str(e)
                })
            except Exception as e:
                error_count += 1
                error_details.append({
                    'linha': index + 1, 
                    'cpf': item.get('cpf'),
                    'erro': f"Erro desconhecido: {str(e)}"
                })
        
        # Registra a ação no log
        self.log_info(
            request=request,
            action='import_vendedores',
            message=f"Importação de vendedores concluída: {created_count} criados, {error_count} com erro",
            data={
                'created_count': created_count,
                'error_count': error_count,
                'file_path': file_path
            }
        )
        
        # Retorna o resultado
        return Response({
            'detail': f"Importação concluída: {created_count} vendedores criados, {error_count} com erro",
            'created_count': created_count,
            'error_count': error_count,
            'errors': error_details if error_count > 0 else None
        })


class VendedorTemplateView(BaseApiView):
    """
    API endpoint para obter um template de exemplo para importação de vendedores.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        """
        Retorna um JSON com os campos necessários para importação de vendedores.
        O cliente pode usar isso para gerar um arquivo CSV ou Excel vazio.
        
        Os campos obrigatórios são:
        - cpf: CPF do vendedor
        - email: Email do vendedor
        - first_name: Nome do vendedor
        - password: Senha inicial do vendedor
        - pix_key: Chave PIX do vendedor
        - pix_type: Tipo de chave PIX (cpf, email, telefone, aleatoria)
        """
        template = [{
            "cpf": "12345678900",
            "email": "vendedor@exemplo.com",
            "first_name": "Nome",
            "last_name": "Sobrenome",
            "password": "senha123",
            "leader_cpf": "00987654321",
            "rg": "1234567",
            "rg_emission_date": "01/01/2000",
            "rg_emission_organ": "SSP",
            "birth_date": "01/01/1990",
            "phone": "11999998888",
            "pix_key": "chave@pix.com",
            "pix_type": "email",
            "company": request.user.company.id if hasattr(request.user, 'company') and request.user.company else ""
        }]
        
        format_param = request.query_params.get('format', 'csv')
        
        if format_param == 'json':
            return Response(template)
        
        elif format_param == 'csv':
            import csv
            import io
            
            # Use HttpResponse em vez de Response para arquivos
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="vendedores_template.csv"'
            
            # Escreva diretamente no response
            writer = csv.DictWriter(response, fieldnames=template[0].keys())
            writer.writeheader()
            writer.writerows(template)
            
            return response
        
        else:
            return Response(template) 