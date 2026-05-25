"""
Script para popular o banco de dados com os bancos nacionais
Use este script para inserir os dados dos bancos no sistema
"""

import django
import os
import sys

# Configuração do Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'corbot.settings')
django.setup()

from bank.models import Bank
from bank.mockdata_bancos import BANCOS_NACIONAIS


def populate_banks():
    """
    Popula o banco de dados com os bancos nacionais
    """
    created_count = 0
    updated_count = 0
    
    for banco_data in BANCOS_NACIONAIS:
        banco, created = Bank.objects.get_or_create(
            code=banco_data["codigo"],
            defaults={
                "name": banco_data["nome"],
                "is_active": banco_data["ativo"]
            }
        )
        
        if created:
            created_count += 1
            print(f"✓ Banco criado: {banco.name} ({banco.code})")
        else:
            # Atualiza dados se o banco já existir
            banco.name = banco_data["nome"]
            banco.is_active = banco_data["ativo"]
            banco.save()
            updated_count += 1
            print(f"↻ Banco atualizado: {banco.name} ({banco.code})")
    
    print(f"\n🎉 Processo concluído!")
    print(f"📊 Bancos criados: {created_count}")
    print(f"🔄 Bancos atualizados: {updated_count}")
    print(f"📈 Total de bancos processados: {created_count + updated_count}")


def delete_all_banks():
    """
    Remove todos os bancos do banco de dados
    CUIDADO: Esta operação não pode ser desfeita!
    """
    count = Bank.objects.count()
    Bank.objects.all().delete()
    print(f"🗑️ Todos os {count} bancos foram removidos do banco de dados")


def show_banks_summary():
    """
    Exibe um resumo dos bancos no banco de dados
    """
    total_banks = Bank.objects.count()
    active_banks = Bank.objects.filter(is_active=True).count()
    inactive_banks = Bank.objects.filter(is_active=False).count()
    
    print(f"\n📋 Resumo dos Bancos no Sistema:")
    print(f"🏦 Total de bancos: {total_banks}")
    print(f"✅ Bancos ativos: {active_banks}")
    print(f"❌ Bancos inativos: {inactive_banks}")
    
    if total_banks > 0:
        print(f"\n📝 Primeiros 10 bancos:")
        for bank in Bank.objects.order_by('name')[:10]:
            status = "✅" if bank.is_active else "❌"
            print(f"  {status} {bank.name} ({bank.code})")


if __name__ == "__main__":
    print("🏛️ Script de População de Bancos Nacionais")
    print("=" * 50)
    
    while True:
        print("\nEscolha uma opção:")
        print("1. Popular bancos no sistema")
        print("2. Exibir resumo dos bancos")
        print("3. Remover todos os bancos (CUIDADO!)")
        print("4. Sair")
        
        opcao = input("\nDigite sua opção (1-4): ").strip()
        
        if opcao == "1":
            print("\n🔄 Populando bancos...")
            populate_banks()
        elif opcao == "2":
            show_banks_summary()
        elif opcao == "3":
            confirmacao = input("\n⚠️  Tem certeza que deseja remover TODOS os bancos? (digite 'CONFIRMAR'): ")
            if confirmacao == "CONFIRMAR":
                delete_all_banks()
            else:
                print("❌ Operação cancelada")
        elif opcao == "4":
            print("👋 Até logo!")
            break
        else:
            print("❌ Opção inválida. Tente novamente.") 