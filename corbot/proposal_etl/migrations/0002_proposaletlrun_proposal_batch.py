import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proposals', '0004_proposalbatch_etl_run'),
        ('proposal_etl', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposaletlrun',
            name='proposal_batch',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='etl_runs',
                to='proposals.proposalbatch',
                verbose_name='lote criado',
            ),
        ),
    ]
