import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bank', '0001_initial'),
        ('proposal_etl', '0002_proposaletlrun_proposal_batch'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProposalEtlBankProfile',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('settings', models.JSONField(blank=True, default=dict, help_text='Defaults por tipo de nó: paginate_http, extract_items, detail_steps[]', verbose_name='configurações')),
                ('notes', models.TextField(blank=True, verbose_name='observações')),
                ('bank', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='etl_profile', to='bank.bank', verbose_name='banco')),
            ],
            options={
                'verbose_name': 'perfil ETL do banco',
                'verbose_name_plural': 'perfis ETL dos bancos',
            },
        ),
    ]
