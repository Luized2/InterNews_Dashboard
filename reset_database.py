# -*- coding: utf-8 -*-
"""
Script para resetar o banco de dados PostgreSQL com encoding UTF-8 correto
Execute este script se tiver problemas de codificação
"""

import subprocess
import sys
import os

def resetar_banco_dados():
    """Remove e recria o banco de dados com encoding UTF-8"""
    
    print("\n" + "="*50)
    print("  RESETAR BANCO DE DADOS - InterNews Pro")
    print("="*50 + "\n")
    
    # Passo 1: Deletar o banco de dados existente
    print("[1/3] Deletando banco de dados existente...")
    try:
        cmd_delete = 'sudo -u postgres psql -c "DROP DATABASE IF EXISTS internews_db;"'
        subprocess.run(cmd_delete, shell=True, check=True)
        print("✅ Banco de dados deletado com sucesso\n")
    except Exception as e:
        print(f"❌ Erro ao deletar banco de dados: {e}\n")
        return False
    
    # Passo 2: Criar novo banco de dados com encoding UTF-8
    print("[2/3] Criando novo banco de dados com encoding UTF-8...")
    try:
        cmd_create = 'sudo -u postgres psql -c "CREATE DATABASE internews_db OWNER internews ENCODING \'UTF8\' LC_COLLATE \'C\' LC_CTYPE \'C\';"'
        subprocess.run(cmd_create, shell=True, check=True)
        print("✅ Banco de dados criado com sucesso\n")
    except Exception as e:
        print(f"❌ Erro ao criar banco de dados: {e}\n")
        return False
    
    # Passo 3: Criar as tabelas
    print("[3/3] Criando tabelas...")
    try:
        from models import criar_tabelas
        criar_tabelas()
        print("✅ Tabelas criadas com sucesso\n")
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}\n")
        return False
    
    print("="*50)
    print("✅ BANCO DE DADOS RESETADO COM SUCESSO!")
    print("="*50 + "\n")
    print("Você pode agora executar a aplicação normalmente:")
    print("  streamlit run internews_com_db.py\n")
    
    return True

if __name__ == "__main__":
    sucesso = resetar_banco_dados()
    sys.exit(0 if sucesso else 1)