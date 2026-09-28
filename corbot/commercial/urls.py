from django.urls import path

from .views import (
    CommercialManagerListCreateView,
    CommercialManagerDetailView,
    CommercialManagerActivationView,
    CommercialTeamView,
    CommercialTeamMemberDetailView,
    CommercialDashboardView,
)

urlpatterns = [
    path('commercial/managers/', CommercialManagerListCreateView.as_view(), name='commercial-manager-list-create'),
    path('commercial/managers/<int:pk>/', CommercialManagerDetailView.as_view(), name='commercial-manager-detail'),
    path(
        'commercial/managers/<int:pk>/activation/',
        CommercialManagerActivationView.as_view(),
        name='commercial-manager-activation',
    ),
    path('commercial/team/', CommercialTeamView.as_view(), name='commercial-team'),
    path('commercial/team/<int:pk>/', CommercialTeamMemberDetailView.as_view(), name='commercial-team-member-detail'),
    path('commercial/dashboard/', CommercialDashboardView.as_view(), name='commercial-dashboard'),
]
