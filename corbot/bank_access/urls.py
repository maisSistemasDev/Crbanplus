from django.urls import path
from .views import (
    BankAccessListCreateView, BankAccessDetailView,
    AccessLogListView,
    # Views para campos de formulário
    BankAccessFormFieldsView, AccessLogFormFieldsView
)

urlpatterns = [
    # Campos de formulário
    path('form-fields/bank-accesses/', BankAccessFormFieldsView.as_view(), name='bank-access-form-fields'),
    path('form-fields/access-logs/', AccessLogFormFieldsView.as_view(), name='access-log-form-fields'),
    
    # Acessos Bancários
    path('bank-accesses/', BankAccessListCreateView.as_view(), name='bank-access-list-create'),
    path('bank-accesses/<uuid:pk>/', BankAccessDetailView.as_view(), name='bank-access-detail'),
    
    # Logs de Acesso
    path('access-logs/', AccessLogListView.as_view(), name='access-log-list'),
] 