"""
URL configuration for corbot project.
"""
from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings
from django.views.static import serve as static_serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    path('api/', include('bank.urls')),
    path('api/', include('proposals.urls')),
    path('api/', include('bank_access.urls')),
    path('api/', include('payments.urls')),
    path('api/', include('commercial.urls')),
    path('api/', include('ai_agent.urls')),
    path('api/', include('proposal_etl.urls')),
    path('api/', include('webhooks.urls')),
]

# Serve uploads do MEDIA_ROOT (logos de banco, anexos, etc.).
# Não dá para usar django.conf.urls.static.static() porque ele retorna []
# quando DEBUG=False. Em produção o NPM faz proxy /media/ → corbanplus_web,
# então registramos a rota explicitamente para o Daphne respondê-la.
# `serve` usa safe_join e impede path traversal acima do document_root.
_media_url = settings.MEDIA_URL.lstrip('/')
urlpatterns += [
    re_path(
        rf'^{_media_url}(?P<path>.*)$',
        static_serve,
        {'document_root': settings.MEDIA_ROOT},
    ),
]