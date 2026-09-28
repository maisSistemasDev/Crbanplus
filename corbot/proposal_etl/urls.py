from django.urls import path

from .views import (
    ProposalEtlFlowListCreateView,
    ProposalEtlFlowDetailView,
    ProposalEtlTestNodeView,
    ProposalEtlRunView,
    ProposalEtlRunListView,
    ProposalEtlMetaView,
    ProposalEtlLayoutFieldsView,
    ProposalEtlGenerateFromDocView,
    ProposalEtlBankProfileView,
    ProposalEtlRunDetailView,
)

urlpatterns = [
    path('proposal-etl/configs/', ProposalEtlFlowListCreateView.as_view(), name='proposal-etl-list'),
    path('proposal-etl/configs/<uuid:pk>/', ProposalEtlFlowDetailView.as_view(), name='proposal-etl-detail'),
    path('proposal-etl/configs/<uuid:pk>/test-node/', ProposalEtlTestNodeView.as_view(), name='proposal-etl-test-node'),
    path('proposal-etl/configs/<uuid:pk>/run/', ProposalEtlRunView.as_view(), name='proposal-etl-run'),
    path('proposal-etl/runs/<uuid:run_id>/', ProposalEtlRunDetailView.as_view(), name='proposal-etl-run-detail'),
    path('proposal-etl/configs/<uuid:pk>/runs/', ProposalEtlRunListView.as_view(), name='proposal-etl-runs'),
    path('proposal-etl/meta/', ProposalEtlMetaView.as_view(), name='proposal-etl-meta'),
    path('proposal-etl/layout-fields/', ProposalEtlLayoutFieldsView.as_view(), name='proposal-etl-layout-fields'),
    path('proposal-etl/generate-from-doc/', ProposalEtlGenerateFromDocView.as_view(), name='proposal-etl-generate'),
    path('proposal-etl/bank-profiles/<uuid:bank_id>/', ProposalEtlBankProfileView.as_view(), name='proposal-etl-bank-profile'),
]
