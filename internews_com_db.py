# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import re
import io
import unicodedata
from dataclasses import dataclass
from typing import List, Dict, Tuple
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# Importar gerenciador de banco de dados
from database_manager import GerenciadorBancoDados

# ==========================================
# 1. CONFIGURAÇÕES E DADOS PADRONIZADOS
# ==========================================

st.set_page_config(
    page_title="Analisador de Atendimentos Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar banco de dados na primeira execução
if 'db_inicializado' not in st.session_state:
    sucesso, msg = GerenciadorBancoDados.inicializar()
    st.session_state.db_inicializado = sucesso
    if not sucesso:
        st.error(f"❌ Erro ao inicializar banco de dados: {msg}")

# LISTA OFICIAL DE TÉCNICOS (Destino Final)
TECNICOS_PADRAO = [
    "Claudia Liliane", 
    "Gustavo Almeida", 
    "Gustavo Kauan", 
    "Alcelio Santos", 
    "Jarbas Fred", 
    "Daniela Nogueira", 
    "Eulis Gaudencio", 
    "Gabriel Gilvan", 
    "Luiz Eduardo", 
    "Ricardo", 
    "Lucas Correa"
]

# MAPA DE NORMALIZAÇÃO
MAPA_TECNICOS = {
    "claudia": "Claudia Liliane",
    "liliane": "Claudia Liliane",
    
    "gustavo almeida": "Gustavo Almeida",
    "gustavo kauan": "Gustavo Kauan",
    "gutavo": "Gustavo Kauan",
    "gustavo": "Gustavo Kauan",
    
    "alcelio": "Alcelio Santos",
    "santos": "Alcelio Santos",
    
    "jarbas": "Jarbas Fred",
    "fred": "Jarbas Fred",
    
    "daniela": "Daniela Nogueira",
    "nogueira": "Daniela Nogueira",
    
    "eulis": "Eulis Gaudencio",
    "gaudencio": "Eulis Gaudencio",
    
    "gabriel": "Gabriel Gilvan",
    "gilvan": "Gabriel Gilvan",
    
    "luiz": "Luiz Eduardo",
    "eduardo": "Luiz Eduardo",
    "luis": "Luiz Eduardo",
    
    "ricardo": "Ricardo",
    
    "lucas": "Lucas Correa",
    "correa": "Lucas Correa",
    
    "ludmilla": "Ludmilla Oliveira",
}

# ==========================================
# 2. MOTOR DE PROCESSAMENTO (BACKEND)
# ==========================================

class LogParser:
    def __init__(self):
        self.re_bloco = re.compile(r"(\d{6}\s+\d{6}.*?)(?=\d{6}\s+\d{6}|\Z)", re.DOTALL)
        self.re_data = re.compile(r"(\d{2}/\d{2}/\d{4})")
        self.re_cliente = re.compile(r"\[SAMUEL\s+(.*?)(?:\n|$)", re.IGNORECASE)
        self.re_suporte = re.compile(r"Suporte[\s:.-]*([^\n\r]+)", re.IGNORECASE)
        self.re_texto_atendimento = re.compile(r"Atendiment.*?\s+(.*?)(?:Internews:|$)", re.DOTALL | re.IGNORECASE)
        self.re_versao = re.compile(r"Internews:\s*([\d\.]+)", re.IGNORECASE)

    def normalizar_texto_base(self, texto: str) -> str:
        """Remove acentos e coloca em minúsculas para busca no dicionário."""
        if not isinstance(texto, str): 
            return ""
        texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
        return texto.strip(" .-:").lower()

    def identificar_tecnico_por_nome(self, nome_bruto: str) -> str:
        """Recebe um fragmento de nome e retorna o nome Padronizado."""
        nome_limpo = self.normalizar_texto_base(nome_bruto)
        
        for chave, valor_padrao in MAPA_TECNICOS.items():
            if chave in nome_limpo:
                return valor_padrao
        
        return nome_bruto.title()

    def extrair_tecnicos(self, texto_bruto: str) -> List[str]:
        """Divide a string de suporte em múltiplos técnicos e normaliza cada um."""
        if not texto_bruto:
            return ["Nao Informado"]
        
        texto_norm = self.normalizar_texto_base(texto_bruto)
        texto_limpo = re.sub(r"(\s+e\s+|\s*/\s*|\s*&\s*|\s*,\s*)", "|", texto_norm)
        
        nomes_encontrados = []
        partes = texto_limpo.split('|')
        
        for parte in partes:
            nome_fragmento = parte.strip()
            if not nome_fragmento: 
                continue
            
            nome_padronizado = self.identificar_tecnico_por_nome(nome_fragmento)
            
            if nome_padronizado:
                nomes_encontrados.append(nome_padronizado)
            
        return nomes_encontrados if nomes_encontrados else ["Nao Informado"]

    def classificar_tipo(self, texto: str) -> str:
        """Classifica o tipo de atendimento baseado no texto."""
        texto_lower = self.normalizar_texto_base(texto)
        if "treinamento" in texto_lower: 
            return "Treinamento"
        elif "erro" in texto_lower: 
            return "Erro"
        elif "rotina" in texto_lower: 
            return "Rotina"
        else: 
            return "Não Identificado"

    def validar_arquivo(self, conteudo_texto: str) -> Tuple[bool, str]:
        """Valida se o arquivo tem o formato esperado."""
        if not conteudo_texto or len(conteudo_texto.strip()) == 0:
            return False, "Arquivo vazio"
        
        if not re.search(r"\d{6}\s+\d{6}", conteudo_texto):
            return False, "Formato inválido: não encontrado padrão de O.S (XXXXXX XXXXXX)"
        
        if not re.search(r"\d{2}/\d{2}/\d{4}", conteudo_texto):
            return False, "Formato inválido: não encontrada data (DD/MM/YYYY)"
        
        blocos = self.re_bloco.findall(conteudo_texto)
        if len(blocos) == 0:
            return False, "Nenhum bloco de atendimento encontrado"
        
        return True, f"Arquivo válido: {len(blocos)} bloco(s) encontrado(s)"

    def processar_arquivo(self, conteudo_texto: str) -> pd.DataFrame:
        """Processa o arquivo e retorna um DataFrame com os dados."""
        registros = []
        blocos = self.re_bloco.findall(conteudo_texto)
        
        for bloco in blocos:
            data = (self.re_data.search(bloco) or ["N/D", "N/D"])[1] if self.re_data.search(bloco) else "N/D"
            os = bloco[:6]
            cliente = (self.re_cliente.search(bloco) or ["", "Cliente Não Identificado"])[1].strip()
            
            suporte_match = self.re_suporte.search(bloco)
            tecnico_raw = suporte_match.group(1) if suporte_match else "Nao Informado"
            tecnico_raw = tecnico_raw.strip(" .")
            
            lista_tecnicos = self.extrair_tecnicos(tecnico_raw)
            
            texto_atend_match = self.re_texto_atendimento.search(bloco)
            texto_atendimento = texto_atend_match.group(1).strip() if texto_atend_match else ""
            
            tipo = self.classificar_tipo(texto_atendimento)
            versao = (self.re_versao.search(bloco) or ["", ""])[1]

            for tech in lista_tecnicos:
                registros.append({
                    "Data": data,
                    "O.S": os,
                    "Cliente": cliente.upper(),
                    "Técnico": tech,
                    "Tipo": tipo,
                    "Versão Internews": versao,
                    "Detalhe Atendimento": texto_atendimento,
                    "Suporte Original (Log)": tecnico_raw
                })
            
        return pd.DataFrame(registros)

# ==========================================
# 3. EXPORTADORES
# ==========================================

class ExportadorDados:
    @staticmethod
    def exportar_excel(df: pd.DataFrame) -> bytes:
        """Exporta para Excel com formatação."""
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Dados')
            
            workbook = writer.book
            worksheet = writer.sheets['Dados']
            
            format_red = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
            worksheet.conditional_format('E2:E1000', {
                'type': 'text',
                'criteria': 'containing',
                'value': 'Não Identificado',
                'format': format_red
            })
            
            format_yellow = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500'})
            worksheet.conditional_format('D2:D1000', {
                'type': 'text',
                'criteria': 'containing',
                'value': 'Nao Informado',
                'format': format_yellow
            })
            
            for column in worksheet.table:
                max_len = max(df[column].astype(str).str.len().max(), len(column))
                worksheet.set_column(worksheet.table.columns[column], max_len + 2)
        
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def exportar_csv(df: pd.DataFrame) -> bytes:
        """Exporta para CSV."""
        return df.to_csv(index=False, encoding='utf-8').encode('utf-8')

    @staticmethod
    def exportar_json(df: pd.DataFrame) -> bytes:
        """Exporta para JSON."""
        return df.to_json(orient='records', ensure_ascii=False, indent=2).encode('utf-8')

# ==========================================
# 4. INTERFACE (STREAMLIT)
# ==========================================

def criar_graficos(df: pd.DataFrame) -> Dict:
    """Cria gráficos interativos com Plotly."""
    graficos = {}
    
    # Gráfico 1: Atendimentos por Técnico
    tech_counts = df['Técnico'].value_counts()
    fig_tech = px.bar(
        x=tech_counts.index, 
        y=tech_counts.values,
        labels={'x': 'Técnico', 'y': 'Quantidade'},
        title='Atendimentos por Técnico',
        color=tech_counts.values,
        color_continuous_scale='Blues'
    )
    fig_tech.update_layout(showlegend=False, height=400)
    graficos['tecnicos'] = fig_tech
    
    # Gráfico 2: Distribuição por Tipo
    tipo_counts = df['Tipo'].value_counts()
    fig_tipo = px.pie(
        values=tipo_counts.values,
        names=tipo_counts.index,
        title='Distribuição por Tipo de Atendimento',
        hole=0.3
    )
    fig_tipo.update_layout(height=400)
    graficos['tipos'] = fig_tipo
    
    # Gráfico 3: Atendimentos por Cliente (Top 10)
    cliente_counts = df['Cliente'].value_counts().head(10)
    fig_cliente = px.bar(
        x=cliente_counts.values,
        y=cliente_counts.index,
        orientation='h',
        labels={'x': 'Quantidade', 'y': 'Cliente'},
        title='Top 10 Clientes',
        color=cliente_counts.values,
        color_continuous_scale='Greens'
    )
    fig_cliente.update_layout(showlegend=False, height=400)
    graficos['clientes'] = fig_cliente
    
    # Gráfico 4: Versões Utilizadas
    versao_counts = df['Versão Internews'].value_counts()
    fig_versao = px.bar(
        x=versao_counts.index,
        y=versao_counts.values,
        labels={'x': 'Versão', 'y': 'Quantidade'},
        title='Versões InterNews Utilizadas',
        color=versao_counts.values,
        color_continuous_scale='Oranges'
    )
    fig_versao.update_layout(showlegend=False, height=400)
    graficos['versoes'] = fig_versao
    
    return graficos

def main():
    st.title("📊 Relatório Mensal - InterNews PRO (com PostgreSQL)")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configurações")
        tab_upload, tab_historico, tab_stats, tab_info = st.tabs(["Upload", "Histórico", "Estatísticas", "Informações"])
        
        with tab_upload:
            st.subheader("Carregar Arquivo")
            uploaded_files = st.file_uploader(
                "Upload de arquivo(s) TXT",
                type=["txt"],
                accept_multiple_files=True,
                help="Selecione um ou mais arquivos de log"
            )
        
        with tab_historico:
            st.subheader("Histórico de Análises")
            sucesso, historico = GerenciadorBancoDados.obter_historico_completo()
            
            if sucesso and historico:
                for i, item in enumerate(historico[:10]):
                    with st.expander(f"📅 {item['timestamp'][:10]} - {item['arquivo']}"):
                        st.write(f"**ID:** {item['id']}")
                        st.write(f"**Registros:** {item['registros']}")
                        st.write(f"**Técnicos:** {item['tecnicos_unicos']}")
                        st.write(f"**Clientes:** {item['clientes_unicos']}")
                        st.write(f"**Tipos:** {item['tipos']}")
                        
                        # Botão para carregar análise anterior
                        if st.button(f"📂 Carregar Análise {item['id']}", key=f"load_{item['id']}"):
                            st.session_state.analise_selecionada = item['id']
                            st.rerun()
            else:
                st.info("Nenhuma análise anterior encontrada")
        
        with tab_stats:
            st.subheader("Estatísticas Gerais")
            sucesso, stats = GerenciadorBancoDados.obter_estatisticas_gerais()
            
            if sucesso:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("📊 Total de Análises", stats['total_analises'])
                    st.metric("👥 Técnicos Únicos", stats['tecnicos_unicos'])
                with col2:
                    st.metric("📝 Total de Registros", stats['total_registros'])
                    st.metric("🏢 Clientes Únicos", stats['clientes_unicos'])
        
        with tab_info:
            st.subheader("Sobre")
            st.markdown("""
            **Versão:** 2.0 Pro (com PostgreSQL)
            
            **Funcionalidades:**
            - ✅ Validação automática de formato
            - ✅ Edição manual de dados
            - ✅ Múltiplos formatos de exportação
            - ✅ Gráficos interativos
            - ✅ **Histórico em PostgreSQL**
            - ✅ Estatísticas gerais
            - ✅ Busca avançada
            
            **Banco de Dados:** PostgreSQL
            **Status:** ✅ Conectado
            """)
    
    # Processamento de arquivos
    if uploaded_files:
        all_dfs = []
        parser = LogParser()
        
        for uploaded_file in uploaded_files:
            try:
                with st.spinner(f"Processando {uploaded_file.name}..."):
                    stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
                    conteudo = stringio.read()
                    
                    # Validação
                    is_valid, msg = parser.validar_arquivo(conteudo)
                    
                    if not is_valid:
                        st.error(f"❌ {uploaded_file.name}: {msg}")
                        continue
                    
                    st.success(f"✅ {uploaded_file.name}: {msg}")
                    
                    # Processamento
                    df = parser.processar_arquivo(conteudo)
                    
                    if df.empty:
                        st.warning(f"⚠️ {uploaded_file.name}: Nenhum registro encontrado")
                        continue
                    
                    all_dfs.append(df)
                    
                    # Salvar no banco de dados
                    tipos_dist = df['Tipo'].value_counts().to_dict()
                    versoes_dist = df['Versão Internews'].value_counts().to_dict()
                    
                    sucesso, msg, analise_id = GerenciadorBancoDados.salvar_analise(
                        nome_arquivo=uploaded_file.name,
                        total_registros=len(df),
                        tecnicos_unicos=df['Técnico'].nunique(),
                        clientes_unicos=df['Cliente'].nunique(),
                        os_unicas=df['O.S'].nunique(),
                        tipos_distribuicao=tipos_dist,
                        versoes_utilizadas=versoes_dist,
                        usuario="admin"
                    )
                    
                    if sucesso:
                        st.info(f"✅ Análise salva no banco de dados (ID: {analise_id})")
                        
                        # Salvar registros
                        sucesso_reg, msg_reg = GerenciadorBancoDados.salvar_registros(
                            analise_id, 
                            df.to_dict('records')
                        )
                        if sucesso_reg:
                            st.success(msg_reg)
                    else:
                        st.error(f"❌ Erro ao salvar: {msg}")
                    
            except Exception as e:
                st.error(f"❌ Erro ao processar {uploaded_file.name}: {str(e)}")
        
        if not all_dfs:
            st.stop()
        
        # Combinar todos os DataFrames
        df_completo = pd.concat(all_dfs, ignore_index=True)
        
        # ==========================================
        # SEÇÃO DE FILTROS
        # ==========================================
        st.divider()
        st.subheader("🔍 Filtros")
        
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            opcoes_tecnicos = sorted(list(set(df_completo["Técnico"].unique()) | set(TECNICOS_PADRAO)))
            opcoes_validas = [t for t in opcoes_tecnicos if t in df_completo["Técnico"].unique()]
            filtro_tecnico = st.multiselect("👤 Técnico", options=opcoes_validas, default=opcoes_validas[:3] if len(opcoes_validas) > 0 else [])
        
        with col_f2:
            filtro_tipo = st.multiselect("📋 Tipo", options=sorted(df_completo["Tipo"].unique()), default=sorted(df_completo["Tipo"].unique()))
        
        with col_f3:
            filtro_cliente = st.multiselect("🏢 Cliente (Top 10)", options=df_completo['Cliente'].value_counts().head(10).index.tolist())
        
        # Aplicar filtros
        df_view = df_completo.copy()
        
        if filtro_tecnico:
            df_view = df_view[df_view["Técnico"].isin(filtro_tecnico)]
        if filtro_tipo:
            df_view = df_view[df_view["Tipo"].isin(filtro_tipo)]
        if filtro_cliente:
            df_view = df_view[df_view["Cliente"].isin(filtro_cliente)]
        
        # ==========================================
        # SEÇÃO DE KPIs
        # ==========================================
        st.divider()
        st.subheader("📈 Resumo Executivo")
        
        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
        
        with kpi1:
            st.metric("📌 O.S Únicas", df_view["O.S"].nunique())
        with kpi2:
            st.metric("👥 Pontuações", len(df_view))
        with kpi3:
            st.metric("⚠️ Erros", len(df_view[df_view['Tipo'] == 'Erro']))
        with kpi4:
            st.metric("📚 Treinamentos", len(df_view[df_view['Tipo'] == 'Treinamento']))
        with kpi5:
            st.metric("🔧 Rotinas", len(df_view[df_view['Tipo'] == 'Rotina']))
        
        # ==========================================
        # SEÇÃO DE GRÁFICOS
        # ==========================================
        st.divider()
        st.subheader("📊 Visualizações")
        
        graficos = criar_graficos(df_view)
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.plotly_chart(graficos['tecnicos'], use_container_width=True)
        with col_g2:
            st.plotly_chart(graficos['tipos'], use_container_width=True)
        
        col_g3, col_g4 = st.columns(2)
        with col_g3:
            st.plotly_chart(graficos['clientes'], use_container_width=True)
        with col_g4:
            st.plotly_chart(graficos['versoes'], use_container_width=True)
        
        # ==========================================
        # SEÇÃO DE EDIÇÃO MANUAL
        # ==========================================
        st.divider()
        st.subheader("✏️ Edição Manual de Dados")
        
        with st.expander("Editar registros antes de exportar"):
            df_editavel = st.data_editor(
                df_view,
                use_container_width=True,
                num_rows="dynamic",
                key="editor"
            )
            
            if not df_editavel.equals(df_view):
                df_view = df_editavel
                st.success("✅ Dados atualizados!")
        
        # ==========================================
        # SEÇÃO DE DETALHAMENTO
        # ==========================================
        st.divider()
        st.subheader("📋 Detalhamento Completo")
        
        col_search, col_display = st.columns([1, 2])
        
        with col_search:
            search_term = st.text_input("🔎 Buscar na tabela:", "")
        
        if search_term:
            df_search = df_view[
                df_view.astype(str).apply(
                    lambda x: x.str.contains(search_term, case=False, na=False).any(), axis=1
                )
            ]
        else:
            df_search = df_view
        
        st.dataframe(df_search, use_container_width=True, height=400)
        
        # ==========================================
        # SEÇÃO DE EXPORTAÇÃO
        # ==========================================
        st.divider()
        st.subheader("💾 Exportar Dados")
        
        col_exp1, col_exp2, col_exp3 = st.columns(3)
        
        with col_exp1:
            excel_data = ExportadorDados.exportar_excel(df_view)
            st.download_button(
                label="📊 Excel",
                data=excel_data,
                file_name=f"relatorio_internews_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.ms-excel"
            )
        
        with col_exp2:
            csv_data = ExportadorDados.exportar_csv(df_view)
            st.download_button(
                label="📄 CSV",
                data=csv_data,
                file_name=f"relatorio_internews_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col_exp3:
            json_data = ExportadorDados.exportar_json(df_view)
            st.download_button(
                label="🔗 JSON",
                data=json_data,
                file_name=f"relatorio_internews_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        # ==========================================
        # ESTATÍSTICAS DETALHADAS
        # ==========================================
        st.divider()
        st.subheader("📊 Estatísticas Detalhadas")
        
        col_stat1, col_stat2 = st.columns(2)
        
        with col_stat1:
            st.markdown("**Distribuição por Técnico:**")
            tech_stats = df_view['Técnico'].value_counts()
            st.bar_chart(tech_stats)
        
        with col_stat2:
            st.markdown("**Distribuição por Tipo:**")
            tipo_stats = df_view['Tipo'].value_counts()
            st.bar_chart(tipo_stats)
        
        # Tabela de resumo
        st.markdown("**Resumo por Técnico:**")
        resumo_tech = df_view.groupby('Técnico').agg({
            'O.S': 'nunique',
            'Cliente': 'nunique',
            'Tipo': lambda x: (x == 'Erro').sum()
        }).rename(columns={'O.S': 'O.S Únicas', 'Cliente': 'Clientes', 'Tipo': 'Erros'})
        st.dataframe(resumo_tech, use_container_width=True)

if __name__ == "__main__":
    main()