# Generated manually

from django.db import migrations, models


def set_master_for_corban_admins(apps, schema_editor):
    BankAccess = apps.get_model('bank_access', 'BankAccess')
    User = apps.get_model('core', 'User')
    admin_ids = User.objects.filter(role='empresa_admin').values_list('id', flat=True)
    BankAccess.objects.filter(user_id__in=admin_ids).update(is_master=True)


class Migration(migrations.Migration):

    dependencies = [
        ('bank_access', '0002_initial'),
        ('core', '0012_importjob_update_existing'),
    ]

    operations = [
        migrations.AddField(
            model_name='bankaccess',
            name='is_master',
            field=models.BooleanField(
                default=False,
                help_text='Master (Corban): comissão direta pela promotora. Desligado: comissão pelos grupos da equipe/vendedor.',
                verbose_name='master',
            ),
        ),
        migrations.AddField(
            model_name='bankaccess',
            name='link',
            field=models.URLField(blank=True, max_length=500, null=True, verbose_name='link'),
        ),
        migrations.AddField(
            model_name='bankaccess',
            name='notes',
            field=models.TextField(blank=True, null=True, verbose_name='observação'),
        ),
        migrations.AlterUniqueTogether(
            name='bankaccess',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='bankaccess',
            constraint=models.UniqueConstraint(
                fields=('bank', 'username'),
                name='unique_bank_access_username',
            ),
        ),
        migrations.RunPython(set_master_for_corban_admins, migrations.RunPython.noop),
    ]
