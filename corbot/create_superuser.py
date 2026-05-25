#!/usr/bin/env python
"""
Script para criar um superusuário automaticamente.
Execute com: python create_superuser.py
"""
import os
import sys
import django

# Configurar o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'corbot.settings')
django.setup()

from django.db import transaction
from core.models import User, Company

# Função principal
def create_superuser():
    # Dados do superusuário
    cpf = '12863843893'  # Substitua pelo CPF desejado
    email = 'danielproença@gmail.com'  # Substitua pelo email desejado
    password = 'rosacruz89D!'  # Substitua pela senha desejada
    first_name = 'Administrador'
    last_name = 'Sistema'

    # Criar empresa para o admin, se necessário
    company_name = 'Auto Promotora'
    company_document = '51057418000176'  # CNPJ sem formatação

    # Verificar se o usuário já existe
    if User.objects.filter(cpf=cpf).exists():
        print(f'Usuário com CPF {cpf} já existe. Pulando criação.')
        return
    
    try:
        with transaction.atomic():
            # Criar ou obter empresa
            company, created = Company.objects.get_or_create(
                document=company_document,
                defaults={
                    'name': company_name,
                    'trading_name': company_name,
                    'email': email,
                    'person_type': 'PJ',
                    'is_active': True,
                    'is_promotora': True  # Marca como empresa promotora
                }
            )
            if created:
                print(f'Empresa "{company_name}" criada com sucesso (Promotora).')
            else:
                print(f'Usando empresa existente: "{company.name}"')
            
            # Criar superusuário
            user = User.objects.create_superuser(
                cpf=cpf,
                email=email,
                password=password
            )
            user.first_name = first_name
            user.last_name = last_name
            user.company = company
            user.save()
            
            print(f'Superusuário criado com sucesso:')
            print(f'CPF: {cpf}')
            print(f'Email: {email}')
            print(f'Senha: {password}')
            print('ATENÇÃO: Altere a senha após o primeiro login por motivos de segurança.')
    
    except Exception as e:
        print(f'Erro ao criar superusuário: {e}')

if __name__ == '__main__':
    create_superuser() 