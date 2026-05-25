from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class APIKeyAuthentication(BaseAuthentication):
    """
    Autenticação via API Key.
    Header esperado: Authorization: Api-Key crb_xxxxxxxx...
    """

    keyword = 'Api-Key'

    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith(f'{self.keyword} '):
            return None

        key = auth_header[len(self.keyword) + 1:].strip()
        return self._authenticate_key(key)

    def _authenticate_key(self, key: str):
        from .models import APIKey

        api_key = APIKey.verify_key(key)
        if api_key is None:
            raise AuthenticationFailed('Chave de API inválida ou expirada.')

        # Atualiza last_used_at sem disparar signals desnecessários
        APIKey.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())

        # Anexa a instância APIKey ao request para uso nas views
        request.api_key = api_key
        return (api_key.created_by, api_key)

    def authenticate_header(self, request):
        return self.keyword
