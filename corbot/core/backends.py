import re
from django.contrib.auth.backends import ModelBackend

from core.auth_profiles import find_users_for_login, normalize_login_document


class DocumentAuthBackend(ModelBackend):
    """
    Backend de autenticação: CPF/CNPJ + senha.
    Com múltiplos perfis, retorna o primeiro que confere (admin Django).
    O fluxo web usa TokenObtainPairView com seleção de perfil.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        username = normalize_login_document(username)
        users = find_users_for_login(username, password)
        return users[0] if users else None

    def get_user(self, user_id):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
