"""
Audita corbans sem admin e CPFs que podem ter perdido perfil corban
(rebaixados para vendedor pelo import de equipe com "atualizar existentes").

Uso:
  python manage.py audit_dual_access
  python manage.py audit_dual_access --csv /tmp/relatorio.csv
"""
import csv
import sys

from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from core.models import User, Company


class Command(BaseCommand):
    help = 'Lista corbans órfãos (sem empresa_admin) e possíveis perfis corban perdidos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            help='Salvar resultado em CSV (corban, document, cpf_sugerido, situacao)',
        )

    def handle(self, *args, **options):
        rows = []

        # Corbans ativos sem nenhum empresa_admin
        companies = Company.objects.filter(
            is_promotora=False,
            is_active=True,
        ).annotate(
            admin_count=Count(
                'users',
                filter=Q(users__role=User.EMPRESA_ADMIN),
            ),
        ).filter(admin_count=0).order_by('name')

        self.stdout.write(self.style.WARNING(
            f'\n=== Corbans SEM administrador ({companies.count()}) ===\n'
        ))

        for company in companies:
            # Vendedor/líder/gerente com CPF de PF no mesmo corban ou login_document
            team = User.objects.filter(
                company=company,
                role__in=(User.VENDEDOR, User.LIDER, User.GERENTE),
            )
            hint = ''
            if team.exists():
                cpfs = ', '.join(
                    u.login_document or u.cpf for u in team[:3]
                )
                hint = f'equipe no corban: {cpfs}'
            rows.append({
                'corban': company.name,
                'document': company.document,
                'cpf_sugerido': '',
                'situacao': f'sem admin — {hint}'.strip(' —'),
            })
            self.stdout.write(
                f'  • {company.name} ({company.document}) {hint}'
            )

        # CPF com perfil de equipe mas sem empresa_admin em nenhum corban
        # (possível rebaixamento: era admin, virou vendedor no mesmo registro)
        self.stdout.write(self.style.WARNING(
            '\n=== CPFs com equipe mas SEM perfil Corban (possível dano) ===\n'
        ))

        team_users = User.objects.filter(
            role__in=(User.VENDEDOR, User.LIDER, User.GERENTE),
        ).select_related('company')

        seen_cpfs = set()
        for user in team_users:
            doc = user.login_document or user.cpf
            if doc in seen_cpfs:
                continue
            seen_cpfs.add(doc)

            has_corban = User.objects.filter(
                Q(login_document=doc) | Q(cpf=doc),
                role=User.EMPRESA_ADMIN,
            ).exists()
            if has_corban:
                continue

            # PF corban cujo document = CPF da pessoa
            pf_corban = Company.objects.filter(
                person_type=Company.PERSON_TYPE_PF,
                document=doc,
                is_promotora=False,
            ).first()

            if pf_corban:
                rows.append({
                    'corban': pf_corban.name,
                    'document': pf_corban.document,
                    'cpf_sugerido': doc,
                    'situacao': (
                        f'PF corban órfão — {user.get_role_display()} '
                        f'em {user.company.name if user.company else "?"}'
                    ),
                })
                self.stdout.write(
                    f'  • CPF {doc}: {user.get_role_display()} '
                    f'({user.company.name if user.company else "?"}) '
                    f'— corban PF "{pf_corban.name}" sem admin'
                )

        if not rows:
            self.stdout.write(self.style.SUCCESS('\nNenhum problema óbvio encontrado.\n'))
        else:
            self.stdout.write(
                f'\nTotal de linhas no relatório: {len(rows)}\n'
                'Recuperação (após deploy com perfis duplos):\n'
                '  1. Reimportar aba Corbans com "Sim, atualizar" OU\n'
                '  2. python manage.py create_corban_profile --cpf ... --company-id ...\n'
            )

        if options.get('csv'):
            path = options['csv']
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=['corban', 'document', 'cpf_sugerido', 'situacao'],
                )
                writer.writeheader()
                writer.writerows(rows)
            self.stdout.write(self.style.SUCCESS(f'CSV salvo em {path}'))
