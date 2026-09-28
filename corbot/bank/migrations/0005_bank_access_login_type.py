# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bank', '0004_increase_name_in_bank_max_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='bank',
            name='access_login_type',
            field=models.CharField(
                choices=[('cpf', 'Login por CPF'), ('email', 'Login por e-mail/outro')],
                default='email',
                help_text='CPF: um acesso por usuário no banco. E-mail: vários acessos por usuário.',
                max_length=10,
                verbose_name='tipo de login no banco',
            ),
        ),
    ]
