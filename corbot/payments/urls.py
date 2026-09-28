"""
URLs para o aplicativo de pagamentos e comissionamento.
"""
from django.urls import path
from .views import (
    CommissionGroupListCreateView,
    CommissionGroupDetailView,
    CommissionGroupByCompanyListCreateView,
    CommissionGroupByCompanyManageView,
    CommissionGroupByUserManageView,
    CommissionGroupMaxRatesView,
    CommissionGroupByCompanyMaxRatesView,
    CommissionListCreateView,
    CommissionDetailView,
    GenerateComissionsView,
    CommissionMirrorView,
    CommissionConsolidatedView,
    CommissionDebitDetailView,
    CommissionBalanceView,
    CommissionGroupFormFieldsView,
    CommissionGroupByCompanyFormFieldsView,
    PaymentFormFieldsView,
    PaymentView,
    WithdrawView,
    UserDebitListCreateView,
    UserDebitDetailView,
)
from .views.claim import ProposalClaimListCreateView
from .views.commission_release import CommissionReleaseView, CommissionExportView, CommissionUpdateStatusView
from .views.commission_group_csv import CommissionGroupExportCSVView, CommissionGroupImportCSVView
from .views.corbanpay_withdraw import CorbanPayWithdrawView
from .views.registration_links import (
    CommissionGroupRegistrationLinkDetailView,
    CommissionGroupRegistrationLinkView,
)

app_name = 'payments'

urlpatterns = [
    # Grupos de comissionamento
    path('commission-groups/', CommissionGroupListCreateView.as_view(), name='commission_group_list'),
    path('commission-groups/<int:pk>/', CommissionGroupDetailView.as_view(), name='commission_group_detail'),
    path('commission-groups/<int:pk>/members/', CommissionGroupByUserManageView.as_view(), name='commission_group_by_user_manage'),
    path(
        'commission-groups/<int:pk>/registration-links/',
        CommissionGroupRegistrationLinkView.as_view(),
        name='commission_group_registration_links',
    ),
    path(
        'commission-groups/<int:pk>/registration-links/<uuid:link_id>/',
        CommissionGroupRegistrationLinkDetailView.as_view(),
        name='commission_group_registration_link_detail',
    ),
    path('commission-groups/<int:group_id>/import-csv/', CommissionGroupImportCSVView.as_view(), name='commission_group_import_csv'),
    path('commission-groups/export-csv-template/', CommissionGroupExportCSVView.as_view(), name='commission_group_export_csv_template'),
    path('commission-groups/by-company/', CommissionGroupByCompanyListCreateView.as_view(), name='commission_group_by_company_list'),
    path('commission-groups/form-fields/', CommissionGroupFormFieldsView.as_view(), name='commission_group_form_fields'),
    path('commission-groups/by-company/form-fields/', CommissionGroupByCompanyFormFieldsView.as_view(), name='commission_group_by_company_form_fields'),
    path('commission-groups/by-company/<int:pk>/', CommissionGroupByCompanyListCreateView.as_view(), name='commission_group_by_company_detail'),
    path('commission-groups/by-company/<int:pk>/companies/', CommissionGroupByCompanyManageView.as_view(), name='commission_group_by_company_manage'),
    path('commission-groups/max-rates/', CommissionGroupMaxRatesView.as_view(), name='commission_group_max_rates'),
    path('commission-groups/by-company/max-rates/', CommissionGroupByCompanyMaxRatesView.as_view(), name='commission_group_by_company_max_rates'),
    # Pagamentos
    path('payments/', PaymentView.as_view(), name='payment_list'),
    path('payments/form-fields/', PaymentFormFieldsView.as_view(), name='payment_form_fields'),
    path('payments/generate-comissions/', GenerateComissionsView.as_view(), name='generate_comissions'),
    path('claims/', ProposalClaimListCreateView.as_view(), name='claim_list_create'),
    path('debits/', UserDebitListCreateView.as_view(), name='debit_list_create'),
    path('debits/<int:pk>/', UserDebitDetailView.as_view(), name='debit_detail'),
    # Saques
    path('withdrawals/', WithdrawView.as_view(), name='withdraw_list'),
    path('withdrawals/corbanpay/', CorbanPayWithdrawView.as_view(), name='corbanpay_withdraw'),
    # Comissões
    path('commissions/', CommissionListCreateView.as_view(), name='commission_list'),
    path('commissions/<int:pk>/', CommissionDetailView.as_view(), name='commission_detail'),
    path('commissions/consolidated/', CommissionConsolidatedView.as_view(), name='commission_consolidated'),
    path('commissions/debit-detail/', CommissionDebitDetailView.as_view(), name='commission_debit_detail'),
    path('commissions/mirror/', CommissionMirrorView.as_view(), name='commission_mirror'),
    path('commissions/balance/', CommissionBalanceView.as_view(), name='commission_balance'),
    path('commissions/release/', CommissionReleaseView.as_view(), name='commission_release'),
    path('commissions/export/', CommissionExportView.as_view(), name='commission_export'),
    path('commissions/update-status/', CommissionUpdateStatusView.as_view(), name='commission_update_status'),
]
