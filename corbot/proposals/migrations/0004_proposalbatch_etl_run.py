import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proposals', '0003_proposal_bank_access'),
        ('proposal_etl', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposalbatch',
            name='etl_run',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='batches',
                to='proposal_etl.proposaletlrun',
                verbose_name='execução ETL',
            ),
        ),
    ]
