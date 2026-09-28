from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bank', '0005_bank_access_login_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='table',
            name='code_in_bank',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='código da tabela'),
        ),
    ]