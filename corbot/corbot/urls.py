"""
URL configuration for corbot project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    path('api/', include('bank.urls')),
    path('api/', include('proposals.urls')),
    path('api/', include('bank_access.urls')),
    path('api/', include('payments.urls')),
    path('api/', include('ai_agent.urls')),
]

# Serve arquivos de mídia via Django (NPM roteia /media/ para este backend)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)