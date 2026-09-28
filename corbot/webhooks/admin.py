from django.contrib import admin

from webhooks.models import WebhookDailyBatch, WebhookDelivery, WebhookEndpoint


@admin.register(WebhookDailyBatch)
class WebhookDailyBatchAdmin(admin.ModelAdmin):
    list_display = ('bank', 'batch_date', 'proposal_batch', 'created_at')
    list_filter = ('batch_date',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(admin.ModelAdmin):
    list_display = ('name', 'bank', 'layout', 'is_active', 'auto_process', 'created_at')
    list_filter = ('is_active', 'auto_process', 'bank')
    search_fields = ('name',)
    readonly_fields = ('secret_token', 'created_at', 'updated_at')


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = ('endpoint', 'status', 'items_count', 'batch_created', 'source_ip', 'created_at')
    list_filter = ('status',)
    readonly_fields = ('raw_payload', 'mapped_rows', 'created_at', 'updated_at')
