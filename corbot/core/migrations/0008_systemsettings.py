from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_apikey'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SystemSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('singleton', models.BooleanField(default=True, editable=False, unique=True)),
                ('corbanpay_base_url', models.URLField(blank=True, null=True, verbose_name='URL base CorbanPay')),
                ('corbanpay_api_key', models.CharField(blank=True, max_length=255, null=True, verbose_name='API key CorbanPay')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_system_settings', to=settings.AUTH_USER_MODEL, verbose_name='atualizado por')),
            ],
            options={
                'verbose_name': 'configuração do sistema',
                'verbose_name_plural': 'configurações do sistema',
            },
        ),
    ]
