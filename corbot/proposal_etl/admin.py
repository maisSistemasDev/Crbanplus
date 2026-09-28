from django.contrib import admin

from .models import ProposalEtlFlow, ProposalEtlRun, ProposalEtlBankProfile


@admin.register(ProposalEtlFlow)
class ProposalEtlFlowAdmin(admin.ModelAdmin):
    list_display = ('name', 'bank', 'is_active', 'updated_at')
    list_filter = ('is_active', 'bank')


@admin.register(ProposalEtlRun)
class ProposalEtlRunAdmin(admin.ModelAdmin):
    list_display = ('flow', 'status', 'started_at', 'rows_written', 'proposal_batch')
    list_filter = ('status',)


@admin.register(ProposalEtlBankProfile)
class ProposalEtlBankProfileAdmin(admin.ModelAdmin):
    list_display = ('bank', 'updated_at')
    search_fields = ('bank__name',)
