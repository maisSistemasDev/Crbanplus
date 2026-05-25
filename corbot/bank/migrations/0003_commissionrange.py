from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('bank', '0002_tablehistory'),
    ]

    operations = [
        migrations.CreateModel(
            name='CommissionRange',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('min_value', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='valor mínimo')),
                ('max_value', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='valor máximo')),
                ('commission_rate', models.DecimalField(decimal_places=2, max_digits=5, verbose_name='taxa de comissionamento')),
                ('table', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='commission_ranges', to='bank.table')),
            ],
            options={
                'verbose_name': 'faixa de comissionamento',
                'verbose_name_plural': 'faixas de comissionamento',
                'ordering': ['min_value'],
            },
        ),
    ]
