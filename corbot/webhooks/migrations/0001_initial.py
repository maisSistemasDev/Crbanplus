import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('bank', '0005_bank_access_login_type'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('proposals', '0004_proposalbatch_etl_run'),
    ]

    operations = [
        migrations.CreateModel(
            name='WebhookEndpoint',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=120, verbose_name='nome')),
                ('secret_token', models.CharField(editable=False, max_length=80, verbose_name='token secreto')),
                ('items_path', models.CharField(blank=True, default='', help_text='Ex.: $.data ou $.items. Vazio = objeto raiz ou lista na raiz.', max_length=255, verbose_name='caminho dos itens no JSON')),
                ('mappings', models.JSONField(blank=True, default=list, verbose_name='mapeamento de campos')),
                ('is_active', models.BooleanField(default=True, verbose_name='ativo')),
                ('auto_process', models.BooleanField(default=True, help_text='Dispara o pipeline de propostas após criar o lote.', verbose_name='processar lote automaticamente')),
                ('bank', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='webhook_endpoints', to='bank.bank', verbose_name='banco')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='webhook_endpoints', to=settings.AUTH_USER_MODEL, verbose_name='criado por')),
                ('layout', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='webhook_endpoints', to='proposals.layout', verbose_name='layout')),
            ],
            options={
                'verbose_name': 'webhook',
                'verbose_name_plural': 'webhooks',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='WebhookDelivery',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('received', 'Recebido'), ('mapped', 'Mapeado'), ('batch_created', 'Lote criado'), ('failed', 'Falhou')], default='received', max_length=20, verbose_name='status')),
                ('raw_payload', models.JSONField(verbose_name='payload bruto')),
                ('mapped_rows', models.JSONField(blank=True, default=list, verbose_name='linhas mapeadas')),
                ('items_count', models.PositiveIntegerField(default=0, verbose_name='itens')),
                ('error_message', models.TextField(blank=True, verbose_name='erro')),
                ('source_ip', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP de origem')),
                ('endpoint', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deliveries', to='webhooks.webhookendpoint', verbose_name='webhook')),
                ('proposal_batch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='webhook_deliveries', to='proposals.proposalbatch', verbose_name='lote')),
            ],
            options={
                'verbose_name': 'entrega de webhook',
                'verbose_name_plural': 'entregas de webhook',
                'ordering': ['-created_at'],
            },
        ),
    ]
