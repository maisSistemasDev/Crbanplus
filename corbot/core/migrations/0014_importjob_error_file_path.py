from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_user_multi_profile'),
    ]

    operations = [
        migrations.AddField(
            model_name='importjob',
            name='error_file_path',
            field=models.CharField(blank=True, max_length=500, verbose_name='arquivo de erros (xlsx)'),
        ),
    ]
