# Generated manually — perfis duplos (vendedor + corban)

from django.db import migrations, models


def populate_profile_fields(apps, schema_editor):
    User = apps.get_model('core', 'User')
    for user in User.objects.all().iterator():
        company_id = str(user.company_id) if user.company_id else 'none'
        user.login_document = user.cpf
        user.username = f'{user.cpf}:{user.role}:{company_id}'
        user.save(update_fields=['login_document', 'username'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_importjob_update_existing'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='login_document',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='CPF/CNPJ usado para agrupar perfis no login',
                max_length=14,
                null=True,
                verbose_name='documento de login',
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='username',
            field=models.CharField(
                blank=True,
                max_length=150,
                null=True,
                unique=True,
                verbose_name='username',
            ),
        ),
        migrations.RunPython(populate_profile_fields, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='user',
            name='login_document',
            field=models.CharField(
                db_index=True,
                help_text='CPF/CNPJ usado para agrupar perfis no login',
                max_length=14,
                verbose_name='documento de login',
            ),
        ),
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(max_length=150, unique=True, verbose_name='username'),
        ),
        migrations.AlterField(
            model_name='user',
            name='cpf',
            field=models.CharField(
                help_text='Documento do perfil (CPF do vendedor ou CNPJ do corban PJ)',
                max_length=14,
                verbose_name='CPF/CNPJ',
            ),
        ),
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(max_length=254, verbose_name='endereço de email'),
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(
                fields=('login_document', 'role', 'company'),
                name='unique_user_profile_per_company',
            ),
        ),
    ]
