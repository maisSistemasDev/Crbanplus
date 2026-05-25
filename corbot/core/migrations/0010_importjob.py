from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_pushsubscription'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ImportJob',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('entity_type', models.CharField(
                    choices=[('vendedor', 'Vendedor'), ('lider', 'Líder'), ('gerente', 'Gerente'), ('corban', 'Corban')],
                    max_length=20, verbose_name='tipo'
                )),
                ('status', models.CharField(
                    choices=[('pending', 'Aguardando'), ('processing', 'Processando'), ('done', 'Concluído'), ('failed', 'Falhou')],
                    default='pending', max_length=20, verbose_name='status'
                )),
                ('total_rows', models.IntegerField(default=0, verbose_name='total de linhas')),
                ('processed_rows', models.IntegerField(default=0, verbose_name='linhas processadas')),
                ('created_count', models.IntegerField(default=0, verbose_name='criados')),
                ('error_count', models.IntegerField(default=0, verbose_name='erros')),
                ('errors', models.JSONField(default=list, verbose_name='detalhes de erros')),
                ('file_path', models.CharField(blank=True, max_length=500, verbose_name='caminho do arquivo')),
                ('created_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='import_jobs',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='criado por',
                )),
            ],
            options={
                'verbose_name': 'job de importação',
                'verbose_name_plural': 'jobs de importação',
                'ordering': ['-created_at'],
            },
        ),
    ]
