"""
WSGI config for corbot project.
"""

import os

from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'corbot.settings')

application = get_wsgi_application()
application = WhiteNoise(application)

# Adiciona o diretório de mídia para ser servido pelo WhiteNoise
media_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'media')
application.add_files(media_root, prefix='media/') 