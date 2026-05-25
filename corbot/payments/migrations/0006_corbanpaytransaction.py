from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0005_commissionrules_range_and_promotora_rules'),
    ]

    operations = [
        migrations.CreateModel(
            name='CorbanPayTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('receiver_id', models.CharField(max_length=100, verbose_name='ID do Recebedor (CorbanPay)')),
                ('pre_payment_id', models.CharField(blank=True, default='', max_length=100, verbose_name='ID do Pré-Pagamento (CorbanPay)')),
                ('withdrawal_link', models.TextField(blank=True, default='', verbose_name='Link de Saque')),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pendente'),
                        ('active', 'Ativo – aguardando saque'),
                        ('withdrawn', 'Sacado'),
                        ('failed', 'Falhou'),
                    ],
                    default='pending',
                    max_length=20,
                    verbose_name='Status',
                )),
                ('error_message', models.TextField(blank=True, default='', verbose_name='Mensagem de erro')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('withdraw', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='corbanpay_transaction',
                    to='payments.withdraw',
                    verbose_name='Saque',
                )),
            ],
            options={
                'verbose_name': 'Transação CorbanPay',
                'verbose_name_plural': 'Transações CorbanPay',
                'ordering': ['-created_at'],
            },
        ),
    ]
