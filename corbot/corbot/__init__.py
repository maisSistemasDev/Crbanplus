# Garante que o Celery seja importado quando o Django for iniciado
from .celery import app as celery_app

__all__ = ('celery_app',) 