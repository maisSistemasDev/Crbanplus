from django.urls import path

from webhooks.views import (
    WebhookEndpointDeliveriesView,
    WebhookEndpointDetailView,
    WebhookEndpointListCreateView,
    WebhookEndpointRegenerateSecretView,
    WebhookEndpointTestView,
    WebhookInboundView,
)

urlpatterns = [
    path('webhooks/endpoints/', WebhookEndpointListCreateView.as_view(), name='webhook-endpoints'),
    path('webhooks/endpoints/<uuid:pk>/', WebhookEndpointDetailView.as_view(), name='webhook-endpoint-detail'),
    path(
        'webhooks/endpoints/<uuid:pk>/regenerate-secret/',
        WebhookEndpointRegenerateSecretView.as_view(),
        name='webhook-endpoint-regenerate-secret',
    ),
    path(
        'webhooks/endpoints/<uuid:pk>/deliveries/',
        WebhookEndpointDeliveriesView.as_view(),
        name='webhook-endpoint-deliveries',
    ),
    path(
        'webhooks/endpoints/<uuid:pk>/test/',
        WebhookEndpointTestView.as_view(),
        name='webhook-endpoint-test',
    ),
    path('webhooks/inbound/<uuid:endpoint_id>/', WebhookInboundView.as_view(), name='webhook-inbound'),
]
