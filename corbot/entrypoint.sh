#!/bin/bash

# Esperar pelo banco de dados
echo "Esperando pelo banco de dados..."
python3 manage.py wait_for_db

# Aplicar migrações
echo "Aplicando migrações..."
python3 manage.py makemigrations --noinput
python3 manage.py migrate

# Coletar arquivos estáticos
echo "Coletando arquivos estáticos..."
python3 manage.py collectstatic --noinput

# Matar processos existentes
echo "Matando processos existentes..."
pkill -f "python3 -m daphne" || true
pkill -f "python3 -m celery" || true
sleep 2

# Iniciar o servidor Daphne (ASGI)
echo "Iniciando servidor Daphne..."
python3 -m daphne -b 0.0.0.0 -p 8000 corbot.asgi:application &

# Iniciar o worker do Celery
echo "Iniciando worker do Celery..."
python3 -m celery -A corbot worker --loglevel=info &

# Manter o script rodando
wait
