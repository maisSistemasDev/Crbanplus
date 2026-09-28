"""
Vincula vendedores/líderes/gerentes sem company_id usando cpf_corban
dos arquivos de import salvos (ImportJob) ou um arquivo informado.

Cenário: import antigo criou vendedores sem company porque cpf_corban
não era resolvido (admin rebaixado ou código sem a coluna).

Uso (simulação — lê jobs de vendedor salvos):
  python manage.py fix_seller_companies

Com arquivo da planilha:
  python manage.py fix_seller_companies --file /caminho/vendedores.xlsx

Aplicar:
  python manage.py fix_seller_companies --apply
  python manage.py fix_seller_companies --apply --file vendedores.xlsx
"""
import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import User, ImportJob
from core.tasks import _read_file, _resolve_company_from_row
from core.utils import normalize_cpf, ensure_unique_matricula


TEAM_ROLES = (User.VENDEDOR, User.LIDER, User.GERENTE)


class Command(BaseCommand):
    help = 'Vincula vendedores sem company_id usando cpf_corban da planilha de import'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Grava company_id (sem esta flag, apenas simula)',
        )
        parser.add_argument(
            '--file',
            help='CSV/XLSX com colunas cpf e cpf_corban (opcional; senão usa ImportJobs)',
        )
        parser.add_argument(
            '--role',
            default='vendedor',
            choices=['vendedor', 'lider', 'gerente'],
            help='Papel a corrigir (default: vendedor)',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        role = options['role']

        if not apply:
            self.stdout.write(self.style.WARNING(
                'Modo simulação. Use --apply para gravar.\n'
            ))

        rows_sources = self._collect_rows(options.get('file'), role)
        if not rows_sources:
            raise CommandError(
                'Nenhuma linha encontrada. Passe --file ou confira ImportJobs de vendedor.'
            )

        fixed = 0
        skipped = 0
        errors = 0

        for source, rows in rows_sources:
            self.stdout.write(self.style.NOTICE(f'\n--- {source} ({len(rows)} linhas) ---\n'))
            for row in rows:
                cpf = normalize_cpf(row.get('cpf') or '')
                if not cpf:
                    skipped += 1
                    continue

                company, err = _resolve_company_from_row(row, None)
                if err or not company:
                    self.stdout.write(self.style.WARNING(
                        f'  ? CPF {cpf}: {err or "sem cpf_corban/company_document na linha"}'
                    ))
                    skipped += 1
                    continue

                users = User.objects.filter(
                    cpf=cpf,
                    role=role,
                    company__isnull=True,
                )
                if not users.exists():
                    skipped += 1
                    continue

                for user in users:
                    self.stdout.write(
                        f'  • CPF {cpf} → corban "{company.name}" ({company.document})'
                    )
                    if not apply:
                        fixed += 1
                        continue
                    try:
                        with transaction.atomic():
                            preferred = row.get('matricula')
                            new_matricula = ensure_unique_matricula(user, company, preferred)
                            user.company = company
                            user.matricula = new_matricula
                            user.save(update_fields=['company', 'matricula'])
                        fixed += 1
                        matricula_note = ''
                        if new_matricula != cpf:
                            matricula_note = f' (matrícula: {new_matricula})'
                        self.stdout.write(self.style.SUCCESS(f'    ✓ vinculado{matricula_note}'))
                    except Exception as exc:
                        errors += 1
                        self.stdout.write(self.style.ERROR(f'    ✗ {exc}'))

        self.stdout.write('')
        if apply:
            self.stdout.write(self.style.SUCCESS(
                f'Concluído: {fixed} vinculado(s), {skipped} ignorado(s), {errors} erro(s).'
            ))
        else:
            self.stdout.write(
                f'Encontrados: {fixed} para vincular, {skipped} ignorado(s). '
                f'Rode com --apply.'
            )

    def _collect_rows(self, file_path: str | None, role: str) -> list[tuple[str, list]]:
        out: list[tuple[str, list]] = []

        if file_path:
            if not os.path.isfile(file_path):
                raise CommandError(f'Arquivo não encontrado: {file_path}')
            out.append((file_path, _read_file(file_path)))
            return out

        jobs = ImportJob.objects.filter(
            entity_type=role,
            status=ImportJob.STATUS_DONE,
        ).order_by('-created_at')

        for job in jobs:
            if job.file_path and os.path.isfile(job.file_path):
                out.append((f'ImportJob {job.id}', _read_file(job.file_path)))

        return out
