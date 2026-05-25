import time
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = 'Aguarda o banco de dados ficar disponível'

    def handle(self, *args, **options):
        self.stdout.write('Aguardando banco de dados...')
        db_conn = None
        attempts = 0
        while not db_conn:
            try:
                db_conn = connections['default']
                db_conn.ensure_connection()
            except (OperationalError, Exception) as exc:
                attempts += 1
                if attempts % 5 == 0:
                    self.stdout.write(
                        f'Banco indisponível, tentativa {attempts} ({type(exc).__name__}: {exc})...'
                    )
                time.sleep(1)
        self.stdout.write(self.style.SUCCESS('Banco de dados disponível!'))
