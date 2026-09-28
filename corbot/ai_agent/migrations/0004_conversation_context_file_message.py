from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ai_agent', '0003_fileindex_filechunk'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversation',
            name='context_file_message',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='context_for_conversations',
                to='ai_agent.message',
                verbose_name='arquivo em contexto',
            ),
        ),
    ]
