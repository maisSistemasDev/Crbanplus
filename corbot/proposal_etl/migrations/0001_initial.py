import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import proposal_etl.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('bank', '0005_bank_access_login_type'),
        ('core', '0013_user_multi_profile'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProposalEtlFlow',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255, verbose_name='nome')),
                ('is_active', models.BooleanField(default=False, verbose_name='ativo')),
                ('flow_definition', models.JSONField(default=proposal_etl.models.default_flow_definition, verbose_name='definição do fluxo')),
                ('bank', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='etl_flows', to='bank.bank', verbose_name='banco')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_etl_flows', to=settings.AUTH_USER_MODEL, verbose_name='criado por')),
            ],
            options={
                'verbose_name': 'fluxo ETL',
                'verbose_name_plural': 'fluxos ETL',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='ProposalEtlRun',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('running', 'Executando'), ('success', 'Sucesso'), ('failed', 'Falhou')], default='running', max_length=20, verbose_name='status')),
                ('started_at', models.DateTimeField(auto_now_add=True, verbose_name='início')),
                ('finished_at', models.DateTimeField(blank=True, null=True, verbose_name='fim')),
                ('fetched_count', models.PositiveIntegerField(default=0, verbose_name='itens obtidos')),
                ('rows_written', models.PositiveIntegerField(default=0, verbose_name='linhas gravadas')),
                ('node_outputs', models.JSONField(blank=True, default=dict, verbose_name='outputs dos nós')),
                ('error_message', models.TextField(blank=True, null=True, verbose_name='erro')),
                ('error_node_id', models.CharField(blank=True, max_length=64, null=True, verbose_name='nó com erro')),
                ('connector_log', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='etl_runs', to='core.connectorlog')),
                ('flow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='runs', to='proposal_etl.proposaletlflow', verbose_name='fluxo')),
            ],
            options={
                'verbose_name': 'execução ETL',
                'verbose_name_plural': 'execuções ETL',
                'ordering': ['-started_at'],
            },
        ),
    ]
