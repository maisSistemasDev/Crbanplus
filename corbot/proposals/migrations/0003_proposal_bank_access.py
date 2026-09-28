# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bank_access', '0003_bankaccess_master_notes_link'),
        ('proposals', '0002_alter_proposal_release_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposal',
            name='bank_access',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='proposals',
                to='bank_access.bankaccess',
                verbose_name='Acesso bancário',
            ),
        ),
    ]
