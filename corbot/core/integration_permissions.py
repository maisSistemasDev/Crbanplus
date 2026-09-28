from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied


class RequiresAPIKey(permissions.BasePermission):
    """Exige autenticação via API Key (não JWT)."""

    message = 'Este endpoint requer Authorization: Api-Key crb_...'

    def has_permission(self, request, view):
        return getattr(request, 'api_key', None) is not None


class HasAPIKeyScope(permissions.BasePermission):
    """
    Verifica escopos da API Key.
    Defina required_api_key_scopes na view, ex.: ['companies:write'].
    """

    message = 'A chave de API não possui o escopo necessário para esta operação.'

    def has_permission(self, request, view):
        api_key = getattr(request, 'api_key', None)
        if not api_key:
            return False
        required = getattr(view, 'required_api_key_scopes', [])
        if not required:
            return True
        key_scopes = set(api_key.scopes or [])
        return all(scope in key_scopes for scope in required)


def assert_api_key_company_access(api_key, company_id) -> None:
    """Chave vinculada a um Corban só opera nesse Corban."""
    if not api_key or not api_key.company_id:
        return
    if str(api_key.company_id) != str(company_id):
        raise PermissionDenied('A chave de API não tem permissão para este Corban.')
