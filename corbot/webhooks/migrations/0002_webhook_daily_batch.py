import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bank', '0005_bank_access_login_type'),
        ('proposals', '0004_proposalbatch_etl_run'),
        ('webhooks', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='WebhookDailyBatch',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('batch_date', models.DateField(verbose_name='data do lote')),
                ('bank', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='webhook_daily_batches', to='bank.bank', verbose_name='banco')),
                ('layout', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='webhook_daily_batches', to='proposals.layout', verbose_name='layout')),
                ('proposal_batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='webhook_daily_batch', to='proposals.proposalbatch', verbose_name='lote')),
            ],
            options={
                'verbose_name': 'lote diário de webhook',
                'verbose_name_plural': 'lotes diários de webhook',
                'ordering': ['-batch_date', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='webhookdailybatch',
            index=models.Index(fields=['bank', 'batch_date'], name='webhooks_we_bank_id_batch_idx'),
        ),
        migrations.AddField(
            model_name='webhookdelivery',
            name='batch_created',
            field=models.BooleanField(default=False, help_text='False quando as linhas foram acrescentadas a um lote aberto do dia.', verbose_name='novo lote criado'),
        ),
    ]
