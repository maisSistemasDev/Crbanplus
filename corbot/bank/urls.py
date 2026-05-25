from django.urls import path
from .views import (
    BankListCreateView, BankDetailView,
    AgreementListCreateView, AgreementDetailView,
    BankAgreementListCreateView, 
    TableListCreateView, TableDetailView,
    BankFormFieldsView, AgreementFormFieldsView, TableFormFieldsView,
    TableCreateBatchView, TableExportCSVView, TablesByBankView, TableHistoryView,
    TableBulkDeleteView
)

urlpatterns = [
    # Campos de formulário
    path('banks/form-fields/', BankFormFieldsView.as_view(), name='bank-form-fields'),
    path('agreements/form-fields/', AgreementFormFieldsView.as_view(), name='agreement-form-fields'),
    path('tables/form-fields/', TableFormFieldsView.as_view(), name='table-form-fields'),
    
    # Bancos
    path('banks/', BankListCreateView.as_view(), name='bank-list-create'),
    path('banks/<uuid:pk>/', BankDetailView.as_view(), name='bank-detail'),
    
    # Convênios
    path('agreements/', AgreementListCreateView.as_view(), name='agreement-list-create'),
    path('agreements/<uuid:pk>/', AgreementDetailView.as_view(), name='agreement-detail'),
    
    # Relações Banco-Convênio
    path('bank-agreements/', BankAgreementListCreateView.as_view(), name='bank-agreement-list-create'), 
    
    # Tabelas (rotas específicas primeiro, genéricas depois)
    path('tables/', TableListCreateView.as_view(), name='table-list-create'),
    path('tables/bulk-delete/', TableBulkDeleteView.as_view(), name='table-bulk-delete'),
    path('tables/create-batch/', TableCreateBatchView.as_view(), name='table-create-batch'),
    path('tables/download-example/', TableCreateBatchView.as_view(), name='table-download-example'),
    path('tables/export-csv/', TableExportCSVView.as_view(), name='table-export-csv'),
    path('tables/export-csv/<uuid:bank_id>/', TableExportCSVView.as_view(), name='table-export-csv-bank'),
    path('tables/by-bank/<uuid:bank_id>/', TablesByBankView.as_view(), name='tables-by-bank'),
    path('tables/<uuid:table_id>/history/', TableHistoryView.as_view(), name='table-history'),
    path('tables/<uuid:pk>/', TableDetailView.as_view(), name='table-detail'),
] 