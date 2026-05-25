import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_permissiontemplate_alter_user_cpf_alter_user_role_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='APIKey',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, verbose_name='nome')),
                ('prefix', models.CharField(editable=False, max_length=12, unique=True, verbose_name='prefixo')),
                ('hashed_key', models.CharField(editable=False, max_length=64, verbose_name='chave hash')),
                ('scopes', models.JSONField(default=list, verbose_name='escopos')),
                ('is_active', models.BooleanField(default=True, verbose_name='ativo')),
                ('expires_at', models.DateTimeField(blank=True, null=True, verbose_name='expira em')),
                ('last_used_at', models.DateTimeField(blank=True, null=True, verbose_name='último uso')),
                ('company', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='api_keys',
                    to='core.company',
                    verbose_name='corban',
                )),
                ('created_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='api_keys',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='criado por',
                )),
            ],
            options={
                'verbose_name': 'chave de API',
                'verbose_name_plural': 'chaves de API',
                'ordering': ['-created_at'],
            },
        ),
    ]
