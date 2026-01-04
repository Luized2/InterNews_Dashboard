# -*- coding: utf-8 -*-
"""
Gerenciador de banco de dados para a aplicação InterNews
Fornece métodos para CRUD de análises e registros
"""

from models import obter_sessao, Analise, Registro, criar_tabelas
from datetime import datetime
from typing import List, Dict, Optional
import json


class GerenciadorBancoDados:
    """Classe para gerenciar operações com o banco de dados"""
    
    @staticmethod
    def inicializar():
        """Inicializa o banco de dados criando as tabelas"""
        try:
            criar_tabelas()
            return True, "Banco de dados inicializado com sucesso"
        except Exception as e:
            return False, f"Erro ao inicializar banco de dados: {str(e)}"
    
    # ==========================================
    # OPERAÇÕES COM ANÁLISES
    # ==========================================
    
    @staticmethod
    def salvar_analise(
        nome_arquivo: str,
        total_registros: int,
        tecnicos_unicos: int,
        clientes_unicos: int,
        os_unicas: int,
        tipos_distribuicao: Dict,
        versoes_utilizadas: Dict,
        usuario: str = "admin",
        notas: str = None
    ) -> tuple:
        """Salva uma nova análise no banco de dados"""
        try:
            sessao = obter_sessao()
            
            analise = Analise(
                nome_arquivo=nome_arquivo,
                total_registros=total_registros,
                tecnicos_unicos=tecnicos_unicos,
                clientes_unicos=clientes_unicos,
                os_unicas=os_unicas,
                tipos_distribuicao=tipos_distribuicao,
                versoes_utilizadas=versoes_utilizadas,
                usuario=usuario,
                notas=notas
            )
            
            sessao.add(analise)
            sessao.commit()
            analise_id = analise.id
            sessao.close()
            
            return True, f"Análise salva com sucesso (ID: {analise_id})", analise_id
        
        except Exception as e:
            return False, f"Erro ao salvar análise: {str(e)}", None
    
    @staticmethod
    def obter_analises(limite: int = 50) -> tuple:
        """Obtém as últimas análises do banco de dados"""
        try:
            sessao = obter_sessao()
            analises = sessao.query(Analise).order_by(Analise.timestamp.desc()).limit(limite).all()
            sessao.close()
            return True, analises
        except Exception as e:
            return False, f"Erro ao obter análises: {str(e)}"
    
    @staticmethod
    def obter_analise_por_id(analise_id: int) -> tuple:
        """Obtém uma análise específica pelo ID"""
        try:
            sessao = obter_sessao()
            analise = sessao.query(Analise).filter(Analise.id == analise_id).first()
            sessao.close()
            
            if analise:
                return True, analise
            else:
                return False, "Análise não encontrada"
        except Exception as e:
            return False, f"Erro ao obter análise: {str(e)}"
    
    @staticmethod
    def obter_historico_completo() -> tuple:
        """Obtém o histórico completo de análises formatado para exibição"""
        try:
            sucesso, analises = GerenciadorBancoDados.obter_analises(limite=1000)
            
            if not sucesso:
                return False, analises
            
            historico = []
            for analise in analises:
                historico.append({
                    "id": analise.id,
                    "timestamp": analise.timestamp.isoformat(),
                    "arquivo": analise.nome_arquivo,
                    "registros": analise.total_registros,
                    "tecnicos_unicos": analise.tecnicos_unicos,
                    "clientes_unicos": analise.clientes_unicos,
                    "os_unicas": analise.os_unicas,
                    "tipos": analise.tipos_distribuicao or {},
                    "versoes": analise.versoes_utilizadas or {},
                    "usuario": analise.usuario,
                    "notas": analise.notas
                })
            
            return True, historico
        except Exception as e:
            return False, f"Erro ao obter histórico: {str(e)}"
    
    @staticmethod
    def atualizar_analise(analise_id: int, notas: str = None) -> tuple:
        """Atualiza informações de uma análise existente"""
        try:
            sessao = obter_sessao()
            analise = sessao.query(Analise).filter(Analise.id == analise_id).first()
            
            if not analise:
                sessao.close()
                return False, "Análise não encontrada"
            
            if notas:
                analise.notas = notas
            
            sessao.commit()
            sessao.close()
            return True, "Análise atualizada com sucesso"
        except Exception as e:
            return False, f"Erro ao atualizar análise: {str(e)}"
    
    @staticmethod
    def deletar_analise(analise_id: int) -> tuple:
        """Deleta uma análise e seus registros associados"""
        try:
            sessao = obter_sessao()
            
            # Deletar registros associados
            sessao.query(Registro).filter(Registro.analise_id == analise_id).delete()
            
            # Deletar análise
            analise = sessao.query(Analise).filter(Analise.id == analise_id).first()
            if analise:
                sessao.delete(analise)
                sessao.commit()
                sessao.close()
                return True, "Análise deletada com sucesso"
            else:
                sessao.close()
                return False, "Análise não encontrada"
        except Exception as e:
            return False, f"Erro ao deletar análise: {str(e)}"
    
    # ==========================================
    # OPERAÇÕES COM REGISTROS
    # ==========================================
    
    @staticmethod
    def salvar_registros(analise_id: int, registros: List[Dict]) -> tuple:
        """Salva múltiplos registros de atendimentos"""
        try:
            sessao = obter_sessao()
            
            for reg in registros:
                registro = Registro(
                    analise_id=analise_id,
                    data=reg.get("Data", ""),
                    os=reg.get("O.S", ""),
                    cliente=reg.get("Cliente", ""),
                    tecnico=reg.get("Técnico", ""),
                    tipo=reg.get("Tipo", ""),
                    versao_internews=reg.get("Versão Internews", ""),
                    detalhe_atendimento=reg.get("Detalhe Atendimento", ""),
                    suporte_original=reg.get("Suporte Original (Log)", "")
                )
                sessao.add(registro)
            
            sessao.commit()
            sessao.close()
            return True, f"{len(registros)} registros salvos com sucesso"
        except Exception as e:
            return False, f"Erro ao salvar registros: {str(e)}"
    
    @staticmethod
    def obter_registros_por_analise(analise_id: int) -> tuple:
        """Obtém todos os registros de uma análise específica"""
        try:
            sessao = obter_sessao()
            registros = sessao.query(Registro).filter(Registro.analise_id == analise_id).all()
            sessao.close()
            return True, registros
        except Exception as e:
            return False, f"Erro ao obter registros: {str(e)}"
    
    @staticmethod
    def obter_registros_por_tecnico(tecnico: str, limite: int = 100) -> tuple:
        """Obtém registros de um técnico específico"""
        try:
            sessao = obter_sessao()
            registros = sessao.query(Registro).filter(
                Registro.tecnico == tecnico
            ).order_by(Registro.data_criacao.desc()).limit(limite).all()
            sessao.close()
            return True, registros
        except Exception as e:
            return False, f"Erro ao obter registros: {str(e)}"
    
    @staticmethod
    def obter_registros_por_cliente(cliente: str, limite: int = 100) -> tuple:
        """Obtém registros de um cliente específico"""
        try:
            sessao = obter_sessao()
            registros = sessao.query(Registro).filter(
                Registro.cliente.ilike(f"%{cliente}%")
            ).order_by(Registro.data_criacao.desc()).limit(limite).all()
            sessao.close()
            return True, registros
        except Exception as e:
            return False, f"Erro ao obter registros: {str(e)}"
    
    @staticmethod
    def obter_estatisticas_gerais() -> tuple:
        """Obtém estatísticas gerais do banco de dados"""
        try:
            sessao = obter_sessao()
            
            total_analises = sessao.query(Analise).count()
            total_registros = sessao.query(Registro).count()
            tecnicos_unicos = sessao.query(Registro.tecnico).distinct().count()
            clientes_unicos = sessao.query(Registro.cliente).distinct().count()
            
            sessao.close()
            
            stats = {
                "total_analises": total_analises,
                "total_registros": total_registros,
                "tecnicos_unicos": tecnicos_unicos,
                "clientes_unicos": clientes_unicos
            }
            
            return True, stats
        except Exception as e:
            return False, f"Erro ao obter estatísticas: {str(e)}"
    
    # ==========================================
    # OPERAÇÕES DE LIMPEZA E MANUTENÇÃO
    # ==========================================
    
    @staticmethod
    def limpar_analises_antigas(dias: int = 30) -> tuple:
        """Remove análises mais antigas que X dias"""
        try:
            from datetime import timedelta
            
            sessao = obter_sessao()
            data_limite = datetime.now() - timedelta(days=dias)
            
            # Obter IDs das análises antigas
            analises_antigas = sessao.query(Analise.id).filter(
                Analise.timestamp < data_limite
            ).all()
            
            ids_para_deletar = [a[0] for a in analises_antigas]
            
            # Deletar registros associados
            for analise_id in ids_para_deletar:
                sessao.query(Registro).filter(Registro.analise_id == analise_id).delete()
            
            # Deletar análises
            sessao.query(Analise).filter(Analise.timestamp < data_limite).delete()
            
            sessao.commit()
            sessao.close()
            
            return True, f"{len(ids_para_deletar)} análises antigas removidas"
        except Exception as e:
            return False, f"Erro ao limpar análises: {str(e)}"
    
    @staticmethod
    def exportar_para_json(analise_id: int) -> tuple:
        """Exporta uma análise completa para JSON"""
        try:
            sucesso, analise = GerenciadorBancoDados.obter_analise_por_id(analise_id)
            if not sucesso:
                return False, "Análise não encontrada"
            
            sucesso, registros = GerenciadorBancoDados.obter_registros_por_analise(analise_id)
            if not sucesso:
                return False, "Erro ao obter registros"
            
            dados = {
                "analise": {
                    "id": analise.id,
                    "timestamp": analise.timestamp.isoformat(),
                    "arquivo": analise.nome_arquivo,
                    "total_registros": analise.total_registros,
                    "tecnicos_unicos": analise.tecnicos_unicos,
                    "clientes_unicos": analise.clientes_unicos,
                    "os_unicas": analise.os_unicas,
                    "tipos": analise.tipos_distribuicao,
                    "versoes": analise.versoes_utilizadas,
                    "usuario": analise.usuario,
                    "notas": analise.notas
                },
                "registros": [
                    {
                        "id": r.id,
                        "data": r.data,
                        "os": r.os,
                        "cliente": r.cliente,
                        "tecnico": r.tecnico,
                        "tipo": r.tipo,
                        "versao": r.versao_internews,
                        "detalhe": r.detalhe_atendimento,
                        "suporte_original": r.suporte_original
                    }
                    for r in registros
                ]
            }
            
            return True, json.dumps(dados, ensure_ascii=False, indent=2)
        except Exception as e:
            return False, f"Erro ao exportar para JSON: {str(e)}"


if __name__ == "__main__":
    # Teste de inicialização
    sucesso, msg = GerenciadorBancoDados.inicializar()
    print(msg)
    
    if sucesso:
        # Teste de estatísticas
        sucesso, stats = GerenciadorBancoDados.obter_estatisticas_gerais()
        if sucesso:
            print(f"\n📊 Estatísticas Gerais:\n{stats}")