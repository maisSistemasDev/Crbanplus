from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ReadFileView, LayoutView, LayoutFormFieldsView, ProposalFieldsView,
    AgreementNamesView, TableNamesView, UserNamesView, ProposalPreviewView,
    ProposalBatchView, ProposalsByBatchView, ProposalListView, StatusPaymentView
)

urlpatterns = [
    path('proposals/', ProposalListView.as_view(), name='proposals'),
    path('proposals/preview-rows/', ReadFileView.as_view(), name='preview-rows'),
    path('proposals/layouts/', LayoutView.as_view(), name='layouts'),
    path('proposals/layouts/<uuid:pk>/', LayoutView.as_view(), name='layouts_detail'),
    path('proposals/layouts/form-fields/', LayoutFormFieldsView.as_view(), name='layouts-form-fields'),
    path('proposals/fields/', ProposalFieldsView.as_view(), name='proposal-fields'),
    path('proposals/agreement-names/', AgreementNamesView.as_view(), name='agreement-names'),
    path('proposals/table-names/', TableNamesView.as_view(), name='table-names'),
    path('proposals/user-names/', UserNamesView.as_view(), name='user-names'),
    path('proposals/preview/<uuid:pk>/', ProposalPreviewView.as_view(), name='preview'),
    path('proposals/batch/', ProposalBatchView.as_view(), name='batch'),
    path('proposals/batch/<uuid:pk>/proposals/', ProposalsByBatchView.as_view(), name='batch_proposals'),
    path('proposals/batch/<uuid:pk>/', ProposalBatchView.as_view(), name='batch_detail'),
    path('proposals/status-payment/', StatusPaymentView.as_view(), name='status-payment'),
] 