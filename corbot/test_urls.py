import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'corbot.settings')
django.setup()

from django.urls import resolve

url = '/api/bank/tables/create-batch/'
print(f'Trying to resolve: {url}')

try:
    match = resolve(url)
    print(f'Match: {match}')
    print(f'View: {match.func}')
    print(f'View name: {match.view_name}')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
