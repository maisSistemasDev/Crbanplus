import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proposal_etl', '0003_proposaletlbankprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposaletlrun',
            name='celery_task_id',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='ID da tarefa Celery'),
        ),
    ]
