from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proposal_etl', '0004_proposaletlrun_celery_task_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposaletlflow',
            name='shared_auth_enabled',
            field=models.BooleanField(
                default=False,
                help_text='Reutiliza a mesma sessão de auth em todos os nós HTTP a cada execução.',
                verbose_name='autenticação compartilhada',
            ),
        ),
        migrations.AddField(
            model_name='proposaletlflow',
            name='shared_auth_type',
            field=models.CharField(
                blank=True,
                default='none',
                max_length=64,
                verbose_name='tipo de auth compartilhada',
            ),
        ),
        migrations.AddField(
            model_name='proposaletlflow',
            name='shared_auth_config',
            field=models.JSONField(
                blank=True,
                default=dict,
                verbose_name='configuração de auth compartilhada',
            ),
        ),
        migrations.AddField(
            model_name='proposaletlrun',
            name='execution_log',
            field=models.JSONField(blank=True, default=list, verbose_name='log de execução'),
        ),
        migrations.AddField(
            model_name='proposaletlrun',
            name='trigger_source',
            field=models.CharField(
                blank=True,
                default='manual',
                help_text='manual ou schedule',
                max_length=20,
                verbose_name='origem do disparo',
            ),
        ),
    ]
