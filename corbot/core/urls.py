from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter

from .views import (
    UserListCreateView, UserDetailView, VendedoresListView,
    LideresCreateListView, ChangeLeaderView, CompanyListCreateView, CompanyDetailView,
    CreateManagerView, CurrentUserView, VendedorDetailView, BatchChangeLeaderView,
    SetupStatusView, SetupView, UserActivationView, CompanyActivationView,
    # Views de campos de formulário
    UserFormFieldsView, UserCreateFormFieldsView, CompanyFormFieldsView,
    ExtraDataFormFieldsView, CreateManagerFormFieldsView,
)
from .views.auth import TokenObtainPairView, TokenSelectProfileView
from .views.views_import import VendedorImportView, VendedorTemplateView
from .views.internal_users import InternalUserViewSet, PermissionTemplateViewSet
from .views.api_keys import APIKeyViewSet
from .views.config import whitelabel_config, CorbanPaySettingsView, AISettingsView
from .views.push import PushSubscriptionView
from .views.portal_content import (
    PortalUsefulLinkListCreateView,
    PortalUsefulLinkDetailView,
    PortalWallMessageListCreateView,
    PortalWallMessageDetailView,
    PortalContentFeedView,
)
from .views.portal_dashboard import PortalDashboardView
from .views.import_job import (
    ImportJobCreateView,
    ImportJobStatusView,
    ImportJobErrorsExportView,
    ImportTemplateView,
)

# Router para ViewSets
router = DefaultRouter()
router.register(r'internal-users', InternalUserViewSet, basename='internal-user')
router.register(r'permission-templates', PermissionTemplateViewSet, basename='permission-template')
router.register(r'api-keys', APIKeyViewSet, basename='api-key')

from core.integrations.views import PublicRegistrationView

urlpatterns = [
    # Router URLs (ViewSets)
    path('', include(router.urls)),
    
    # Configurações de Whitelabel
    path('config/whitelabel/', whitelabel_config, name='whitelabel-config'),
    path('config/corbanpay/', CorbanPaySettingsView.as_view(), name='corbanpay-config'),
    path('config/ai/', AISettingsView.as_view(), name='ai-config'),
    
    # Campos de formulário
    path('form-fields/users/', UserFormFieldsView.as_view(), name='user-form-fields'),
    path('form-fields/users/create/', UserCreateFormFieldsView.as_view(), name='user-create-form-fields'),
    path('form-fields/companies/', CompanyFormFieldsView.as_view(), name='company-form-fields'),
    path('form-fields/extra-data/', ExtraDataFormFieldsView.as_view(), name='extra-data-form-fields'),
    path('form-fields/managers/', CreateManagerFormFieldsView.as_view(), name='create-manager-form-fields'),
    
    # Autenticação
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/select-profile/', TokenSelectProfileView.as_view(), name='token_select_profile'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Empresas
    path('companies/', CompanyListCreateView.as_view(), name='company-list-create'),
    path('companies/<uuid:pk>/', CompanyDetailView.as_view(), name='company-detail'),
    path('companies/<uuid:pk>/activation/', CompanyActivationView.as_view(), name='company-activation'),
    
    # Usuários
    path('users/', UserListCreateView.as_view(), name='user-list-create'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('users/<int:pk>/activation/', UserActivationView.as_view(), name='user-activation'),
    path('users/sellers/', VendedoresListView.as_view(), name='sellers-list'),
    path('users/leaders/', LideresCreateListView.as_view(), name='leaders-create'),
    path('users/sellers/<int:pk>/', VendedorDetailView.as_view(), name='seller-detail'),
    path('users/<int:pk>/change_leader/', ChangeLeaderView.as_view(), name='change-leader'),
    path('users/batch_change_leader/', BatchChangeLeaderView.as_view(), name='batch-change-leader'),
    path('users/managers/', CreateManagerView.as_view(), name='create-manager'),
    path('users/me/', CurrentUserView.as_view(), name='current-user'),
    path('users/form-fields/', UserFormFieldsView.as_view(), name='user-form-fields'),
    # Importação de vendedores
    path('users/import/sellers/', VendedorImportView.as_view(), name='sellers-import'),
    path('users/import/sellers/template/', VendedorTemplateView.as_view(), name='sellers-import-template'),
    

    
    # Setup
    path('setup/status/', SetupStatusView.as_view(), name='setup-status'),
    path('setup/', SetupView.as_view(), name='setup'),

    # Push Notifications
    path('push/subscribe/', PushSubscriptionView.as_view(), name='push-subscribe'),

    # Conteúdo do portal (links úteis e mural)
    path('portal/useful-links/', PortalUsefulLinkListCreateView.as_view(), name='portal-useful-links'),
    path('portal/useful-links/<int:pk>/', PortalUsefulLinkDetailView.as_view(), name='portal-useful-link-detail'),
    path('portal/wall-messages/', PortalWallMessageListCreateView.as_view(), name='portal-wall-messages'),
    path('portal/wall-messages/<int:pk>/', PortalWallMessageDetailView.as_view(), name='portal-wall-message-detail'),
    path('portal/content-feed/', PortalContentFeedView.as_view(), name='portal-content-feed'),
    path('portal/dashboard/', PortalDashboardView.as_view(), name='portal-dashboard'),

    # Importação em lote
    path('import/', ImportJobCreateView.as_view(), name='import-create'),
    path('import/<uuid:job_id>/', ImportJobStatusView.as_view(), name='import-status'),
    path('import/<uuid:job_id>/errors.xlsx/', ImportJobErrorsExportView.as_view(), name='import-errors-export'),
    path('import/template/<str:entity_type>/', ImportTemplateView.as_view(), name='import-template'),

    # Documentação
    path('docs/', include('core.docs.urls')),

    # Integração externa (API Key)
    path('integrations/v1/', include('core.integrations.urls')),
    path('public/registration/<str:token>/', PublicRegistrationView.as_view(), name='public-registration'),
] 