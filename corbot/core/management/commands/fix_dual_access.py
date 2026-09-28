"""
Detecta vendedores/líderes/gerentes com corban PF (documento = CPF da pessoa)
sem perfil empresa_admin e cria o acesso duplo (perfil Corban separado).

Cenário típico: import de vendedores com "atualizar existentes" rebaixou
empresa_admin → vendedor. O corban PF (document = CPF) ficou órfão.

Critério: existe Company PF com document == CPF do usuário de equipe,
mas não há User empresa_admin nesse corban.

Uso (simulação — padrão):
  python manage.py fix_dual_access

Aplicar de fato:
  python manage.py fix_dual_access --apply

Um CPF só:
  python manage.py fix_dual_access --apply --cpf 12345678900
"""
import re

from django.db import transaction

from core.auth_profiles import build_profile_username
from core.models import User, Company, ExtraData
from django.core.management.base import BaseCommand


TEAM_ROLES = (User.VENDEDOR, User.LIDER, User.GERENTE)


class Command(BaseCommand):
    help = (
        'Cria perfil empresa_admin para quem tem corban PF (documento=CPF) '
        'e perfil de equipe, restaurando acesso duplo'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Executa as alterações (sem esta flag, apenas simula)',
        )
        parser.add_argument(
            '--cpf',
            help='Processar apenas este CPF',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        cpf_filter = re.sub(r'\D', '', options['cpf']) if options.get('cpf') else None

        if not apply:
            self.stdout.write(self.style.WARNING(
                'Modo simulação (dry-run). Use --apply para criar os perfis.\n'
            ))

        team_qs = User.objects.filter(
            role__in=TEAM_ROLES,
            is_active=True,
        ).select_related('company')

        if cpf_filter:
            from django.db.models import Q
            team_qs = team_qs.filter(Q(cpf=cpf_filter) | Q(login_document=cpf_filter))

        # Um processamento por CPF
        seen_cpfs: set[str] = set()
        created = 0
        skipped = 0
        pending = 0

        for team_user in team_qs.order_by('cpf'):
            cpf = team_user.login_document or team_user.cpf
            cpf = re.sub(r'\D', '', cpf)
            if len(cpf) != 11 or cpf in seen_cpfs:
                continue
            if cpf_filter and cpf != cpf_filter:
                continue
            seen_cpfs.add(cpf)

            own_corban = Company.objects.filter(
                document=cpf,
                person_type=Company.PERSON_TYPE_PF,
                is_promotora=False,
            ).first()

            if not own_corban:
                skipped += 1
                continue

            if User.objects.filter(
                role=User.EMPRESA_ADMIN,
                company=own_corban,
            ).exists():
                skipped += 1
                continue

            pending += 1
            team_company = team_user.company.name if team_user.company else '?'
            own_match = (
                team_user.company_id == own_corban.id
                or (team_user.company and team_user.company.document == cpf)
            )
            hint = (
                'vendedor no próprio corban PF'
                if own_match
                else f'equipe em "{team_company}", corban PF órfão'
            )

            self.stdout.write(
                f'  • CPF {cpf} — {team_user.get_role_display()} — '
                f'corban "{own_corban.name}" ({hint})'
            )

            if not apply:
                continue

            try:
                with transaction.atomic():
                    admin = self._create_admin_profile(team_user, own_corban, cpf)
                created += 1
                self.stdout.write(self.style.SUCCESS(
                    f'    ✓ Perfil Corban criado: user_id={admin.id} '
                    f'(equipe preservada: user_id={team_user.id})'
                ))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'    ✗ Erro: {exc}'))

        self.stdout.write('')
        if apply:
            self.stdout.write(self.style.SUCCESS(
                f'Concluído: {created} perfil(is) Corban criado(s), '
                f'{skipped} ignorado(s), {pending - created} pendente(s) com erro.'
            ))
        else:
            self.stdout.write(
                f'Encontrados: {pending} CPF(s) para corrigir, '
                f'{skipped} ignorado(s). Rode com --apply para executar.'
            )

    def _create_admin_profile(self, team_user: User, company: Company, cpf: str) -> User:
        email = company.email or team_user.email
        if not email:
            email = f'{cpf}@corban.local'

        admin = User(
            username=build_profile_username(cpf, User.EMPRESA_ADMIN, company.id),
            cpf=cpf,
            login_document=cpf,
            email=email,
            first_name=team_user.first_name or company.name,
            last_name=team_user.last_name or '',
            role=User.EMPRESA_ADMIN,
            company=company,
            is_active=True,
        )
        # Mesma senha do perfil de equipe (hash copiado — login unificado)
        admin.password = team_user.password
        admin.save()

        team_extra = ExtraData.objects.filter(user=team_user).first()
        if team_extra and (team_extra.pix_key or team_extra.pix_type):
            ExtraData.objects.update_or_create(
                user=admin,
                defaults={
                    'pix_key': team_extra.pix_key,
                    'pix_type': team_extra.pix_type,
                    'phone': team_extra.phone,
                },
            )

        return admin
