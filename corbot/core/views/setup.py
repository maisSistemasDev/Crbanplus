"""
Views para configuração inicial do sistema.
Permite criar a promotora e o usuário admin na primeira execução.
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from core.models import User, Company
from core.serializers import CompanySerializer

logger = logging.getLogger(__name__)


class SetupStatusView(APIView):
    """Retorna se o sistema já foi inicializado (se existe algum usuário)."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({'initialized': User.objects.exists()})


class SetupView(APIView):
    """Cria a promotora e o usuário admin. Só funciona se não existir nenhum usuário."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        if User.objects.exists():
            return Response(
                {'detail': 'Sistema já inicializado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        company_data = request.data.get('company', {})
        user_data = request.data.get('user', {})

        # Normalizar company_data - mapear 'cnpj' para 'document' e remover formatação
        import re
        if 'cnpj' in company_data and 'document' not in company_data:
            # Aceitar 'cnpj' como sinônimo de 'document' para retrocompatibilidade
            company_data['document'] = company_data.pop('cnpj')
        
        # Remover formatação do document (pontos, traços, barras)
        if 'document' in company_data and company_data['document']:
            company_data['document'] = re.sub(r'\D', '', company_data['document'])
        
        # Definir person_type como PJ se não informado (para retrocompatibilidade)
        if 'person_type' not in company_data:
            company_data['person_type'] = 'PJ'

        # Validate company
        company_serializer = CompanySerializer(data=company_data)
        if not company_serializer.is_valid():
            return Response(
                {'company_errors': company_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate required user fields
        cpf = user_data.get('cpf')
        password = user_data.get('password')
        email = user_data.get('email')
        
        # Normalizar CPF (remover formatação)
        if cpf:
            cpf = re.sub(r'\D', '', cpf)
        if not cpf or not password or not email:
            return Response(
                {'detail': 'CPF, email e senha são obrigatórios.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create promotora company
        company = company_serializer.save()
        # Mark as promotora (main company)
        company.is_promotora = True
        company.save(update_fields=['is_promotora'])

        # Create admin user (promotora admin has no company FK)
        user = User.objects.create_user(
            cpf=cpf,
            password=password,
            email=email,
            first_name=user_data.get('first_name', ''),
            last_name=user_data.get('last_name', ''),
            role=User.ADMIN,
            is_staff=True,
            is_superuser=True,
        )

        logger.info(f'Sistema inicializado — promotora: {company.name}, admin: {user.cpf}')

        return Response(
            {
                'detail': 'Sistema inicializado com sucesso.',
                'company_id': str(company.id),
                'user_id': user.id,
            },
            status=status.HTTP_201_CREATED,
        )
