"""
Cria um perfil Corban (empresa_admin) separado para quem já é vendedor/líder/gerente.

Uso:
  python manage.py create_corban_profile \\
    --cpf 12345678900 \\
    --company-id <uuid-do-corban> \\
    --email admin@corban.com \\
    --password 'Senha@123'
"""
from django.core.management.base import BaseCommand, CommandError

from core.models import User, Company


class Command(BaseCommand):
    help = 'Cria perfil empresa_admin independente para CPF que já tem perfil de equipe'

    def add_arguments(self, parser):
        parser.add_argument('--cpf', required=True, help='CPF da pessoa (mesmo do vendedor)')
        parser.add_argument('--company-id', required=True, help='UUID do corban')
        parser.add_argument('--email', required=True)
        parser.add_argument('--password', required=True)
        parser.add_argument('--first-name', default='')

    def handle(self, *args, **options):
        import re
        cpf = re.sub(r'\D', '', options['cpf'])
        company = Company.objects.filter(id=options['company_id']).first()
        if not company:
            raise CommandError('Corban não encontrado.')

        if User.objects.filter(role=User.EMPRESA_ADMIN, company=company).exists():
            raise CommandError('Este corban já possui administrador.')

        team_profile = User.objects.filter(login_document=cpf).exclude(
            role=User.EMPRESA_ADMIN,
        ).first()

        first_name = options['first_name'] or (team_profile.first_name if team_profile else company.name)

        user = User.objects.create_user(
            cpf=cpf,
            login_document=cpf,
            password=options['password'],
            email=options['email'],
            first_name=first_name,
            role=User.EMPRESA_ADMIN,
            company=company,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Perfil Corban criado: user_id={user.id}, username={user.username}'
        ))
        if team_profile:
            self.stdout.write(
                f'Perfil de equipe preservado: user_id={team_profile.id} ({team_profile.get_role_display()})'
            )
