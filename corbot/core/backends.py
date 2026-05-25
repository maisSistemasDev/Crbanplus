import re
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class DocumentAuthBackend(ModelBackend):
    """
    Backend de autenticação customizado que permite login com CPF ou CNPJ.
    Normaliza o documento (remove pontos, traços) antes de buscar o usuário.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        
        # Normaliza o documento (remove formatação)
        username = re.sub(r'\D', '', username)
        
        try:
            # Busca usuário pelo CPF (que é o USERNAME_FIELD)
            user = User.objects.get(cpf=username)
        except User.DoesNotExist:
            # Se não encontrou, tenta buscar pelo documento da empresa (para empresa_admin)
            # Isso permite que empresa_admin de corban PJ faça login com o CNPJ
            try:
                from core.models import Company
                company = Company.objects.get(document=username)
                # Busca o empresa_admin vinculado a esta empresa
                user = User.objects.get(
                    company=company,
                    role=User.EMPRESA_ADMIN
                )
            except (Company.DoesNotExist, User.DoesNotExist, User.MultipleObjectsReturned):
                return None
        
        # Verifica a senha
        if user.check_password(password):
            return user
        
        return None
