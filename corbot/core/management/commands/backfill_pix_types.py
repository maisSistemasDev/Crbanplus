"""
Corrige/infera pix_type em ExtraData existentes e opcionalmente reimporta
chaves PIX de um arquivo Excel/CSV (colunas: cpf, pix_key, pix_type).
"""
from django.core.management.base import BaseCommand

from core.models import ExtraData, User
from core.tasks import _read_file
from core.utils import normalize_cpf, normalize_import_row, resolve_pix_fields


class Command(BaseCommand):
    help = 'Infere pix_type faltante ou reimporta PIX de planilha por CPF'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            help='Caminho para Excel/CSV com cpf, pix_key e pix_type',
        )
        parser.add_argument(
            '--infer-only',
            action='store_true',
            help='Só infere pix_type a partir de pix_key já salvo no banco',
        )

    def handle(self, *args, **options):
        updated = 0

        if options['file']:
            rows = _read_file(options['file'])
            for row in rows:
                row = normalize_import_row(row)
                cpf = normalize_cpf(row.get('cpf') or row.get('admin_cpf'))
                if not cpf:
                    continue
                try:
                    user = User.objects.get(cpf=cpf)
                except User.DoesNotExist:
                    self.stderr.write(f'CPF {cpf} não encontrado')
                    continue

                pix_key, pix_type = resolve_pix_fields(
                    row.get('pix_key') or row.get('admin_pix_key'),
                    row.get('pix_type') or row.get('admin_pix_type'),
                )
                if not pix_key and not pix_type:
                    continue

                ExtraData.objects.update_or_create(
                    user=user,
                    defaults={'pix_key': pix_key, 'pix_type': pix_type},
                )
                updated += 1

        if options['infer_only'] or not options['file']:
            for extra in ExtraData.objects.exclude(pix_key__isnull=True).exclude(pix_key=''):
                _, pix_type = resolve_pix_fields(extra.pix_key, extra.pix_type)
                if pix_type and extra.pix_type != pix_type:
                    extra.pix_type = pix_type
                    extra.save(update_fields=['pix_type'])
                    updated += 1

        self.stdout.write(self.style.SUCCESS(f'{updated} registro(s) atualizado(s)'))
