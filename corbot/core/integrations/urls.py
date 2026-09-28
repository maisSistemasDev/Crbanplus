from django.urls import path

from core.integrations.views import (
    CommissionGroupIntegrationCreateView,
    CommissionGroupRegistrationLinkCreateView,
    CorbanIntegrationCreateView,
    RegistrationLinkRevokeView,
    SellerIntegrationCreateView,
)

urlpatterns = [
    path('corbans/', CorbanIntegrationCreateView.as_view(), name='integration-corban-create'),
    path('sellers/', SellerIntegrationCreateView.as_view(), name='integration-seller-create'),
    path(
        'commission-groups/',
        CommissionGroupIntegrationCreateView.as_view(),
        name='integration-commission-group-create',
    ),
    path(
        'commission-groups/<int:pk>/registration-links/',
        CommissionGroupRegistrationLinkCreateView.as_view(),
        name='integration-registration-link-create',
    ),
    path(
        'registration-links/<uuid:link_id>/revoke/',
        RegistrationLinkRevokeView.as_view(),
        name='integration-registration-link-revoke',
    ),
]
