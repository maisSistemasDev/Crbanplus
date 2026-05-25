#!/usr/bin/env python
"""
Script para criar um superusuário via linha de comando.
Uso: 
    python add_superuser.py --cpf 000.000.000-00 --email admin@corbot.com.br --password admin123 --nome "Admin" --sobrenome "Sistema"
"""
import os
import sys
import django
import argparse

# Configurar o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'corbot.settings')
django.setup()

from django.db import transaction
from core.models import User, Company

def main():
    # Configurar os argumentos da linha de comando
    parser = argparse.ArgumentParser(description='Cria um superusuário no sistema Corbot.')
    parser.add_argument('--cpf', required=True, help='CPF do superusuário (ex: 000.000.000-00)')
    parser.add_argument('--email', required=True, help='Email do superusuário')
    parser.add_argument('--password', required=True, help='Senha do superusuário')
    parser.add_argument('--nome', default='Administrador', help='Primeiro nome do superusuário')
    parser.add_argument('--sobrenome', default='Sistema', help='Sobrenome do superusuário')
    parser.add_argument('--empresa', default='Corbot', help='Nome da empresa')
    parser.add_argument('--document', default='00000000000100', help='CPF ou CNPJ da empresa (sem formatação)')
    parser.add_argument('--person-type', default='PJ', choices=['PF', 'PJ'], help='Tipo de pessoa (PF ou PJ)')
    
    args = parser.parse_args()
    print(args)
    
    # Verificar se o usuário já existe
    if User.objects.filter(cpf=args.cpf).exists():
        print(f'Usuário com CPF {args.cpf} já existe. Pulando criação.')
        return
    
    try:
        with transaction.atomic():
            # Criar ou obter empresa
            company, created = Company.objects.get_or_create(
                document=args.document,
                defaults={
                    'name': args.empresa,
                    'trading_name': args.empresa,
                    'email': args.email,
                    'person_type': args.person_type,
                    'is_active': True
                }
            )
            if created:
                print(f'Empresa "{args.empresa}" criada com sucesso.')
            else:
                print(f'Usando empresa existente: "{company.name}"')
            
            # Criar superusuário
            user = User.objects.create_superuser(
                cpf=args.cpf,
                email=args.email,
                password=args.password
            )
            user.first_name = args.nome
            user.last_name = args.sobrenome
            user.company = company
            user.save()
            
            print(f'Superusuário criado com sucesso:')
            print(f'CPF: {args.cpf}')
            print(f'Email: {args.email}')
            print(f'Senha: {args.password}')
            print('ATENÇÃO: Altere a senha após o primeiro login por motivos de segurança.')
    
    except Exception as e:
        print(f'Erro ao criar superusuário: {e}')

if __name__ == '__main__':
    main() 