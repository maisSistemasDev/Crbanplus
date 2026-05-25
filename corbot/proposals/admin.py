from django.contrib import admin
from .models import Proposal, Layout, LayoutField, ProposalFile, ProposalBatch



@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ('contract_number', 'seller', 'bank', 'agreement', 
                   'table', 'company', 'status', 'disbursement_date')
    list_filter = ('status', 'bank', 'agreement', 'company', 'created_at')
    search_fields = ('contract_number', 'seller__first_name', 
                    'seller__last_name', 'seller__cpf')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'


@admin.register(Layout)
class LayoutAdmin(admin.ModelAdmin):
    list_display = ('id', 'bank', 'created_at')
    list_filter = ('bank', 'created_at')
    search_fields = ('bank__name',)
    readonly_fields = ('id', 'created_at', 'updated_at')

@admin.register(LayoutField)
class LayoutFieldAdmin(admin.ModelAdmin):
    list_display = ('name', 'data_type', 'index', 'header_name')
    list_filter = ('data_type', 'index')
    search_fields = ('name', 'header_name')
    readonly_fields = ('id', 'created_at', 'updated_at')

@admin.register(ProposalFile)
class ProposalFileAdmin(admin.ModelAdmin):
    list_display = ('id', 'uploaded_at')
    readonly_fields = ('id', 'created_at', 'updated_at', 'uploaded_at')

@admin.register(ProposalBatch)
class ProposalBatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'processed_at', 'processed_rows', 'total_rows')
    list_filter = ('status', 'processed_at')
    readonly_fields = ('id', 'created_at', 'updated_at', 'processed_at')
