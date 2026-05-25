from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import permissions, status
from django.conf import settings

from core.base_views import BaseApiView
from core.models import SystemSettings
from core.permissions import IsPromotoraAdmin


@api_view(['GET'])
@permission_classes([AllowAny])
def whitelabel_config(request):
    """
    Retorna as configurações de whitelabel do sistema.
    Endpoint público para permitir que o frontend obtenha as configurações antes do login.
    """
    return Response({
        'system_name': settings.WHITELABEL_SYSTEM_NAME,
        'logo_url': settings.WHITELABEL_LOGO_URL,
    })


class CorbanPaySettingsView(BaseApiView):
    """
    Configuração da integração CorbanPay.
    Apenas admin da promotora pode visualizar/editar.
    """

    permission_classes = [permissions.IsAuthenticated, IsPromotoraAdmin]

    def get(self, request):
        settings_obj = SystemSettings.get_solo()
        return Response({
            'corbanpay_base_url': settings_obj.corbanpay_base_url or '',
            'corbanpay_api_key': settings_obj.masked_corbanpay_api_key,
            'corbanpay_api_key_configured': bool(settings_obj.corbanpay_api_key),
            'updated_at': settings_obj.updated_at,
            'updated_by': settings_obj.updated_by.id if settings_obj.updated_by else None,
        })

    def patch(self, request):
        settings_obj = SystemSettings.get_solo()

        base_url = request.data.get('corbanpay_base_url', None)
        api_key = request.data.get('corbanpay_api_key', None)

        if base_url is not None:
            base_url = str(base_url).strip().rstrip('/')
            if base_url and not (base_url.startswith('http://') or base_url.startswith('https://')):
                return Response(
                    {'detail': 'A URL base do CorbanPay deve iniciar com http:// ou https://.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            settings_obj.corbanpay_base_url = base_url or None

        if api_key is not None:
            api_key = str(api_key).strip()
            settings_obj.corbanpay_api_key = api_key or None

        settings_obj.updated_by = request.user
        settings_obj.save()

        self.log_info(
            request=request,
            action='update_corbanpay_settings',
            message='Configurações do CorbanPay atualizadas',
        )

        return self.get(request)
