from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_systemsettings_ai_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='importjob',
            name='updated_count',
            field=models.IntegerField(default=0, verbose_name='atualizados'),
        ),
        migrations.AddField(
            model_name='importjob',
            name='update_existing',
            field=models.BooleanField(default=False, verbose_name='atualizar existentes'),
        ),
    ]
