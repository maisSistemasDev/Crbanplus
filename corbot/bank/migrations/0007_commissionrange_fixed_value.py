from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bank', '0006_table_code_in_bank'),
    ]

    operations = [
        migrations.AddField(
            model_name='commissionrange',
            name='fixed_value',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                default=None,
                max_digits=10,
                null=True,
                verbose_name='valor fixo de comissão',
            ),
        ),
        migrations.AlterField(
            model_name='commissionrange',
            name='commission_rate',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                default=0,
                max_digits=5,
                null=True,
                verbose_name='taxa de comissionamento',
            ),
        ),
    ]
