"""
Modelos de banco de dados para a aplicação InterNews
Usando SQLAlchemy ORM para gerenciar as tabelas
"""

# -*- coding: utf-8 -*-
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Configuração do banco de dados com suporte a UTF-8
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://internews:internews123@localhost/internews_db?client_encoding=utf8"
)

# Criar engine com suporte completo a UTF-8
engine = create_engine(
    DATABASE_URL, 
    echo=False,
    connect_args={'client_encoding': 'utf8'}
)

# Base para os modelos
Base = declarative_base()

# ==========================================
# MODELOS
# ==========================================

class Analise(Base):
    """Modelo para armazenar histórico de análises"""
    __tablename__ = "analises"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)
    nome_arquivo = Column(String(255), nullable=False)
    total_registros = Column(Integer, nullable=False)
    tecnicos_unicos = Column(Integer, nullable=False)
    clientes_unicos = Column(Integer, nullable=False)
    os_unicas = Column(Integer, nullable=False)
    tipos_distribuicao = Column(JSON, nullable=True)  # {"Erro": 5, "Treinamento": 3, ...}
    versoes_utilizadas = Column(JSON, nullable=True)  # {"1.0": 10, "2.0": 5, ...}
    usuario = Column(String(100), default="admin", nullable=False)
    notas = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<Analise(id={self.id}, arquivo='{self.nome_arquivo}', registros={self.total_registros})>"


class Registro(Base):
    """Modelo para armazenar registros individuais de atendimentos"""
    __tablename__ = "registros"
    
    id = Column(Integer, primary_key=True)
    analise_id = Column(Integer, nullable=False)  # FK para Analise
    data = Column(String(10), nullable=False)  # DD/MM/YYYY
    os = Column(String(20), nullable=False)
    cliente = Column(String(255), nullable=False)
    tecnico = Column(String(100), nullable=False)
    tipo = Column(String(50), nullable=False)
    versao_internews = Column(String(20), nullable=True)
    detalhe_atendimento = Column(Text, nullable=True)
    suporte_original = Column(String(255), nullable=True)
    data_criacao = Column(DateTime, default=datetime.now, nullable=False)
    
    def __repr__(self):
        return f"<Registro(id={self.id}, os='{self.os}', tecnico='{self.tecnico}')>"


class Usuario(Base):
    """Modelo para gerenciar usuários (opcional)"""
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    ativo = Column(Integer, default=1, nullable=False)
    data_criacao = Column(DateTime, default=datetime.now, nullable=False)
    
    def __repr__(self):
        return f"<Usuario(id={self.id}, username='{self.username}')>"


# ==========================================
# FUNÇÕES DE INICIALIZAÇÃO
# ==========================================

def criar_tabelas():
    """Cria todas as tabelas no banco de dados"""
    Base.metadata.create_all(engine)
    print("✅ Tabelas criadas com sucesso!")


def obter_sessao():
    """Retorna uma nova sessão do banco de dados"""
    Session = sessionmaker(bind=engine)
    return Session()


def limpar_banco_dados():
    """Remove todas as tabelas (USE COM CUIDADO!)"""
    Base.metadata.drop_all(engine)
    print("⚠️ Todas as tabelas foram removidas!")


if __name__ == "__main__":
    criar_tabelas()