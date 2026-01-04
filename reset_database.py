# -*- coding: utf-8 -*-
"""
Script para resetar o banco de dados PostgreSQL (Compatível Windows/Linux)
"""

import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
from models import DATABASE_URL, criar_tabelas

def get_maintenance_url():
    """
    Cria uma URL de conexão para o banco de dados de manutenção 'postgres'.
    Tenta usar as credenciais do models.py, mas conectando ao banco 'postgres'
    para permitir deletar o banco 'internews_db'.
    """
    # Substitui o nome do banco alvo pelo banco padrão 'postgres'
    if "internews_db" in DATABASE_URL:
        return DATABASE_URL.replace("internews_db", "postgres")
    return "postgresql://postgres:postgres@localhost/postgres" # Fallback padrão

def resetar_banco_dados():
    print("\n" + "="*50)
    print("  RESETAR BANCO DE DADOS - InterNews Pro (Windows/Linux)")
    print("="*50 + "\n")

    # URL para manutenção (conecta no 'postgres' para poder apagar o outro)
    maintenance_url = get_maintenance_url()
    
    print(f"[INFO] Conectando ao banco de sistema para manutenção...")
    
    try:
        # Configuração essencial: isolation_level="AUTOCOMMIT" 
        # PostgreSQL não permite CREATE/DROP DATABASE dentro de uma transação
        engine = create_engine(maintenance_url, isolation_level="AUTOCOMMIT")
        
        with engine.connect() as conn:
            # Passo 1: Forçar desconexão de usuários ativos (para evitar erro de "banco em uso")
            print("[1/4] Desconectando sessões ativas no 'internews_db'...")
            conn.execute(text("""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = 'internews_db'
                AND pid <> pg_backend_pid();
            """))
            
            # Passo 2: Deletar o banco
            print("[2/4] Deletando banco de dados existente...")
            conn.execute(text("DROP DATABASE IF EXISTS internews_db"))
            print("✅ Banco de dados deletado.")

            # Passo 3: Criar o banco novo
            print("[3/4] Criando novo banco de dados (UTF-8)...")
            # Nota: O dono (OWNER) deve ser o usuário que você criou (internews)
            conn.execute(text("CREATE DATABASE internews_db WITH OWNER internews ENCODING 'UTF8'"))
            print("✅ Banco de dados criado.")

    except ProgrammingError as e:
        print(f"\n❌ ERRO DE PERMISSÃO OU SQL:")
        print(f"Detalhe: {e}")
        print("\nDICA: Verifique se o usuário 'internews' tem permissão de 'CREATEDB'.")
        print("Se não tiver, execute no SQL Shell: ALTER USER internews CREATEDB;")
        return False
    except Exception as e:
        print(f"\n❌ ERRO GERAL: {e}")
        print(f"Tentamos conectar em: {maintenance_url}")
        print("Verifique se o serviço do PostgreSQL está rodando e a senha está correta em models.py")
        return False

    # Passo 4: Criar tabelas (usando o models.py original)
    print("[4/4] Recriando tabelas...")
    try:
        # Importante: O engine do models.py conecta no banco novo 'internews_db'
        # precisamos garantir que ele use a conexão limpa
        criar_tabelas()
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        return False

    print("\n" + "="*50)
    print("✅ RESET CONCLUÍDO COM SUCESSO!")
    print("="*50 + "\n")
    return True

if __name__ == "__main__":
    sucesso = resetar_banco_dados()
    sys.exit(0 if sucesso else 1)