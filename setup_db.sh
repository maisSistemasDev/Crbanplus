#!/bin/bash
set -e

echo "==> Subindo o container do PostgreSQL..."
docker compose up -d postgres
echo "==> Aguardando o PostgreSQL ficar pronto..."
until docker compose exec postgres pg_isready -U postgres -d corbot > /dev/null 2>&1; do
  sleep 1
done
echo "==> PostgreSQL pronto."

echo "==> Rodando as migrations..."
docker compose run --rm web python manage.py makemigrations
docker compose run --rm web python manage.py migrate

echo "==> Populando bancos (mockdata)..."
docker compose run --rm web python manage.py shell -c "exec(open('bank/populate_banks.py').read())" 2>/dev/null || true

echo ""
read -p "Deseja criar um superusuário? [s/N] " criar_super
if [[ "$criar_super" =~ ^[sS]$ ]]; then
  docker compose run --rm web python manage.py createsuperuser
fi

echo ""
echo "==> Banco de dados configurado com sucesso!"
