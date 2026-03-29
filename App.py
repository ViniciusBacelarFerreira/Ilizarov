import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import datetime
import sqlite3

# Importações da base de dados e utilitários
from database import init_db, obter_df_paciente, obter_df_completo, DB_NAME, obter_classificacao
from utils import carregar_css

# Importação dos Módulos Clínicos
import modulos.arthro_map as arthro_map
import modulos.nhfs as nhfs
import modulos.osteoporose as osteoporose
import modulos.start_back as start_back
import modulos.spine_sage as spine_sage
import modulos.rotator_cuff as rotator_cuff
import modulos.osteosarcoma as osteosarcoma
import modulos.foot_ankle_id as foot_ankle_id
import modulos.distal_radius as distal_radius
import modulos.distal_radius_instability as distal_radius_instability
import modulos.proximal_humerus_outcomes as proximal_humerus_outcomes

# ==========================================
# CONFIGURAÇÃO INICIAL E ESTADO DA SESSÃO
# ==========================================
st.set_page_config(page_title="OrtoPreditor Ilizarov", layout="wide", page_icon="🦴")
carregar_css()

# CSS Extra para transformar o Radio Button em "Abas Flutuantes" (Pills)
st.markdown("""
<style>
    div.row-widget.stRadio > div { flex-direction: row; flex-wrap: wrap; gap: 10px; justify-content: center; }
    div.row-widget.stRadio > div > label { 
        background-color: var(--secondary-background-color); 
        padding: 10px 20px; 
        border-radius: 30px; 
        border: 1px solid rgba(128, 128, 128, 0.2); 
        cursor: pointer; 
        transition: all 0.3s ease; 
    }
    div.row-widget.stRadio > div > label:hover { 
        background-color: rgba(76, 175, 80, 0.1); 
        border-color: #4caf50; 
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    div.row-widget.stRadio > div > label [data-testid="stMarkdownContainer"] p { font-weight: 700; margin: 0; color: var(--text-color); }
</style>
""", unsafe_allow_html=True)

init_db()

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'paciente_ativo' not in st.session_state:
    st.session_state.paciente_ativo = {"nome": "", "mae": "", "prontuario": ""}

# Variável de controle para o Dashboard Anatômico
if 'modulo_selecionado' not in st.session_state:
    st.session_state.modulo_selecionado = None

# Lista atualizada com todos os módulos
lista_modulos = [
    'arthro_map_res', 'nhfs_res', 'osteo_res', 'start_back_res', 
    'spinesage_res', 'rotator_cuff_res', 'osteosarcoma_res', 
    'foot_ankle_id_res', 'distal_radius_res', 'distal_radius_instability_res',
    'proximal_humerus_outcomes_res'
]
for mod in lista_modulos:
    if mod not in st.session_state:
        st.session_state[mod] = None

SENHA_CORRETA = "hugv1869"

# ==========================================
# TELA DE LOGIN
# ==========================================
if not st.session_state.autenticado:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.markdown("<h1 class='main-title' style='font-size: 2.8rem;'>OrtoPreditor <span class='ilizarov-text'>Ilizarov</span></h1>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 1rem; opacity: 0.8; margin-bottom: 30px;'>Acesso Restrito - Hospital Universitário Getúlio Vargas</p>", unsafe_allow_html=True)
        
        senha = st.text_input("Senha Institucional:", type="password", placeholder="Insira a senha...")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("DESBLOQUEAR ACESSO", use_container_width=True):
            if senha == SENHA_CORRETA:
                st.session_state.autenticado = True
                st.rerun()
            else: 
                st.error("Senha incorreta. Tente novamente.")
        
        st.markdown("<hr style='opacity: 0.15; margin: 30px 0 20px 0;'>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 0.85rem; font-weight: 600; opacity: 0.7; margin: 0; text-transform: uppercase; letter-spacing: 1px;'>Made By Vinícius Bacelar Ferreira</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==========================================
# NAVEGAÇÃO / MENU LATERAL 
# ==========================================
with st.sidebar:
    st.markdown("""
        <div style='text-align: center; padding: 10px 0;'>
            <h4 style='color: var(--text-color); margin: 0; font-weight: 600; opacity: 0.8;'>HUGV - UFAM</h4>
            <h2 style='color: #1b5e20; margin: 5px 0 15px 0; font-weight: 800; letter-spacing: -0.5px;'>Ilizarov<span style='color: #4caf50;'>AI</span></h2>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("<hr style='margin: 0; opacity: 0.2;'>", unsafe_allow_html=True)
    
    st.markdown("<div class='sidebar-section-title'>Navegação Principal</div>", unsafe_allow_html=True)
    nav = st.radio("Módulos:", ["🏠 Área de Trabalho", "📊 Gestão & Analytics"], label_visibility="collapsed")
    st.markdown("<hr style='margin: 15px 0; opacity: 0.2;'>", unsafe_allow_html=True)
    
    if st.session_state.paciente_ativo['prontuario']:
        st.markdown("<div class='sidebar-section-title'>Paciente em Consulta</div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="sidebar-patient-card">
            <div style="font-size: 0.8rem; color: var(--text-color); opacity: 0.7;">Prontuário: <b>{st.session_state.paciente_ativo['prontuario']}</b></div>
            <div style="font-weight: bold; font-size: 1.05rem; color: var(--text-color); margin-top: 5px; line-height: 1.2;">👤 {st.session_state.paciente_ativo['nome']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("❌ Fechar Prontuário", type="primary", use_container_width=True):
            st.session_state.paciente_ativo = {"nome": "", "mae": "", "prontuario": ""}
            st.session_state.modulo_selecionado = None
            for mod in lista_modulos:
                st.session_state[mod] = None
            st.rerun()
        st.markdown("<hr style='margin: 15px 0; opacity: 0.2;'>", unsafe_allow_html=True)

    if st.button("🚪 Sair do Sistema", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.paciente_ativo = {"nome": "", "mae": "", "prontuario": ""}
        st.session_state.modulo_selecionado = None
        st.rerun()
        
    st.markdown("<br><br><p style='text-align: center; font-size: 0.75rem; font-weight: bold; opacity: 0.5;'>Made By Vinícius Bacelar Ferreira</p>", unsafe_allow_html=True)

# ==========================================
# ÁREA DE TRABALHO
# ==========================================
if nav == "🏠 Área de Trabalho":
    if not st.session_state.paciente_ativo['prontuario']:
        st.markdown("<h1 class='main-title'>OrtoPreditor <span class='ilizarov-text'>Ilizarov</span></h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 1.15rem; opacity: 0.85; max-width: 900px; margin: 15px auto 35px auto;'>Sistema de apoio à decisão cirúrgica em Ortopedia e Traumatologia. Utiliza modelos preditivos baseados na literatura médica para estimar riscos de complicações, mortalidade e prognósticos de reabilitação.</p>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<div class='input-card'><h3>🔍 Acessar Prontuário Antigo</h3>", unsafe_allow_html=True)
            conn = sqlite3.connect(DB_NAME)
            df_b = pd.read_sql("SELECT DISTINCT prontuario as 'Prontuário', paciente as 'Paciente', mae as 'Mãe' FROM avaliacoes", conn)
            conn.close()
            
            if not df_b.empty:
                termo_busca = st.text_input("🔍 Buscar por Nome ou Prontuário:", placeholder="Digite para filtrar os pacientes...", label_visibility="collapsed")
                if termo_busca:
                    df_filtrado = df_b[df_b['Paciente'].str.contains(termo_busca, case=False, na=False) | 
                                       df_b['Prontuário'].str.contains(termo_busca, case=False, na=False)]
                else:
                    df_filtrado = df_b
                
                if not df_filtrado.empty:
                    lista = [""] + [f"{r['Prontuário']} - {r['Paciente']}" for _, r in df_filtrado.iterrows()]
                    sel = st.selectbox("Resultados encontrados:", lista)
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("Abrir Prontuário Selecionado", use_container_width=True) and sel:
                        id_p = sel.split(" - ")[0]
                        dados = df_b[df_b['Prontuário'] == id_p].iloc[0]
                        st.session_state.paciente_ativo = {"prontuario": id_p, "nome": dados['Paciente'], "mae": dados['Mãe']}
                        st.session_state.modulo_selecionado = None
                        st.rerun()
                else:
                    st.warning("Nenhum paciente encontrado.")
            else: 
                st.info("Sem registros na base de dados no momento.")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with c2:
            st.markdown("<div class='input-card'><h3>➕ Registrar Novo Paciente</h3>", unsafe_allow_html=True)
            nn = st.text_input("Nome Completo do Paciente:")
            nm = st.text_input("Nome da Mãe:")
            np = st.text_input("Número do Prontuário:")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Registrar e Iniciar Atendimento", use_container_width=True) and nn and np:
                st.session_state.paciente_ativo = {"nome": nn, "mae": nm, "prontuario": str(np)}
                st.session_state.modulo_selecionado = None
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            
    else:
        st.markdown(f"""
        <div class="patient-header">
            <div>
                <p style="font-size:0.85rem; opacity:0.8; margin-bottom:5px; text-transform:uppercase; letter-spacing: 1px;">Prontuário Eletrônico Ativo</p>
                <h2 style="margin-top:0; margin-bottom:0;">👤 {st.session_state.paciente_ativo["nome"]}</h2>
            </div>
            <div style="text-align: right;">
                <p style="margin-bottom:10px; font-size: 1.1rem;">Prontuário: <b>{st.session_state.paciente_ativo["prontuario"]}</b></p>
                <button style="background: rgba(255,255,255,0.2); border: 1px solid white; color: white; border-radius: 8px; padding: 6px 15px; cursor: pointer;" onclick="window.location.reload();">Atualizar Ficha</button>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # =======================================================
        # ROTEADOR DO DASHBOARD ANATÔMICO (ABAS FLUTUANTES)
        # =======================================================
        if st.session_state.modulo_selecionado is None:
            st.markdown("<h3 style='text-align: center;'>🗺️ Navegação Clínica Integrada</h3>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: gray;'>Selecione a região anatômica abaixo para acessar as calculadoras preditivas:</p>", unsafe_allow_html=True)
            
            categoria_escolhida = st.radio(
                "Navegação",
                ["🧬 Sistêmico e Ósseo", "💪 Membro Superior", "🦵 Membro Inferior", "🦴 Coluna", "🖨️ Relatórios"],
                horizontal=True,
                label_visibility="collapsed"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)

            # --- MENU METABÓLICO ---
            if categoria_escolhida == "🧬 Sistêmico e Ósseo":
                with st.expander("🔸 Osteometabolismo", expanded=True):
                    if st.button("🩸 Osteoporose (Diretrizes Lancet)", use_container_width=True):
                        st.session_state.modulo_selecionado = 'osteoporose'
                        st.rerun()
                with st.expander("🔸 Oncologia Óssea", expanded=True):
                    if st.button("🎗️ Nomograma de Osteossarcoma (Sobrevida 5 Anos)", use_container_width=True):
                        st.session_state.modulo_selecionado = 'osteosarcoma'
                        st.rerun()

            # --- MEMBRO SUPERIOR ---
            elif categoria_escolhida == "💪 Membro Superior":
                with st.expander("🔸 Ombro", expanded=True):
                    if st.button("💪 RoHI (Risco de Falha no Manguito Rotador)", use_container_width=True):
                        st.session_state.modulo_selecionado = 'rotator_cuff'
                        st.rerun()
                    if st.button("💪 Adequação do Seguimento (Fratura Úmero Proximal)", use_container_width=True):
                        st.session_state.modulo_selecionado = 'proximal_humerus_outcomes'
                        st.rerun()
                with st.expander("🔸 Braço"):
                    st.info("⏳ Módulos para o braço em desenvolvimento...")
                with st.expander("🔸 Cotovelo"):
                    st.info("⏳ Módulos para o cotovelo em desenvolvimento...")
                with st.expander("🔸 Antebraço"):
                    st.info("⏳ Módulos para o antebraço em desenvolvimento...")
                with st.expander("🔸 Mão e Punho", expanded=True):
                    if st.button("✋ Risco de Instabilidade (Pós-Redução Rádio Distal)", use_container_width=True):
                        st.session_state.modulo_selecionado = 'distal_radius_instability'
                        st.rerun()
                    if st.button("✋ Risco Funcional (Fratura de Rádio Distal)", use_container_width=True):
                        st.session_state.modulo_selecionado = 'distal_radius'
                        st.rerun()

            # --- MEMBRO INFERIOR ---
            elif categoria_escolhida == "🦵 Membro Inferior":
                with st.expander("🔸 Quadril", expanded=True):
                    if st.button("🦵 Arthro-MAP (Risco Pós-Op Artroplastia de Quadril)", use_container_width=True, key="am_quadril"):
                        st.session_state.modulo_selecionado = 'arthro_map'
                        st.rerun()
                    if st.button("🩼 NHFS (Mortalidade em Fratura do Fêmur)", use_container_width=True):
                        st.session_state.modulo_selecionado = 'nhfs'
                        st.rerun()
                with st.expander("🔸 Coxa"):
                    st.info("⏳ Módulos para a coxa em desenvolvimento...")
                with st.expander("🔸 Joelho", expanded=True):
                    if st.button("🦵 Arthro-MAP (Risco Pós-Op Artroplastia de Joelho)", use_container_width=True, key="am_joelho"):
                        st.session_state.modulo_selecionado = 'arthro_map'
                        st.rerun()
                with st.expander("🔸 Perna"):
                    st.info("⏳ Módulos para a perna em desenvolvimento...")
                with st.expander("🔸 Tornozelo e Pé", expanded=True):
                    if st.button("🦶 Risco Infeccioso (Cirurgia de Pé e Tornozelo)", use_container_width=True):
                        st.session_state.modulo_selecionado = 'foot_ankle_id'
                        st.rerun()

            # --- COLUNA VERTEBRAL ---
            elif categoria_escolhida == "🦴 Coluna":
                with st.expander("🔸 Coluna Cervical", expanded=True):
                    if st.button("🧠 SpineSage (Complicações Pós-Operatórias)", use_container_width=True, key="ss_cerv"):
                        st.session_state.modulo_selecionado = 'spine_sage'
                        st.rerun()
                with st.expander("🔸 Coluna Torácica", expanded=True):
                    if st.button("🧠 SpineSage (Complicações Pós-Operatórias)", use_container_width=True, key="ss_tor"):
                        st.session_state.modulo_selecionado = 'spine_sage'
                        st.rerun()
                with st.expander("🔸 Coluna Lombar", expanded=True):
                    if st.button("🏃 STarT Back (Triagem de Dor Lombar)", use_container_width=True):
                        st.session_state.modulo_selecionado = 'start_back'
                        st.rerun()
                        
            # --- RELATÓRIOS ---
            elif categoria_escolhida == "🖨️ Relatórios":
                st.markdown("#### Emissão de Documentos")
                if st.button("📄 Gerar Relatório Oficial em A4", type="primary", use_container_width=True):
                    st.session_state.modulo_selecionado = 'relatorio'
                    st.rerun()

            # --- PAINEL DE RESULTADOS CONSOLIDADOS NA TELA INICIAL ---
            st.markdown("<hr style='opacity: 0.2; margin: 40px 0;'>", unsafe_allow_html=True)
            st.subheader("📊 Resumo Clínico do Paciente")
            df_p = obter_df_paciente(st.session_state.paciente_ativo['prontuario'])
            if not df_p.empty:
                df_l = df_p.sort_values(by="Data/Hora").groupby("Avaliação Clínica").last().reset_index()
                cols = st.columns(3)
                for i, r in df_l.iterrows():
                    v = float(r['Resultado (%)'])
                    _, cor = obter_classificacao(v, r['Tipo'])
                    with cols[i % 3]:
                        st.markdown(f"""
                        <div class="dashboard-card b-{cor}">
                            <div>
                                <div style="font-weight:700; opacity:0.8; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.5px;">{r["Avaliação Clínica"]}</div>
                                <div class="card-value t-{cor}">{v}%</div>
                            </div>
                            <div>
                                <div style="font-weight:bold; font-size: 1.1rem;" class="t-{cor}">{r["Classificação"]}</div>
                                <div style="font-size:0.8rem; opacity:0.6; margin-top: 8px;">{r["Data/Hora"]}</div>
                            </div>
                        </div><br>
                        """, unsafe_allow_html=True)
            else: 
                st.info("Nenhuma avaliação registrada no prontuário deste paciente. Navegue pelo menu acima para iniciar.")

        # =======================================================
        # RENDERIZAÇÃO ISOLADA DO MÓDULO SELECIONADO
        # =======================================================
        else:
            # Botão de retorno global para a Navegação Clínica
            if st.button("⬅️ Voltar à Navegação Anatômica"):
                st.session_state.modulo_selecionado = None
                st.rerun()
                
            st.markdown("<hr style='opacity: 0.1; margin: 10px 0 20px 0;'>", unsafe_allow_html=True)
            
            # Roteamento para a interface correta do módulo
            if st.session_state.modulo_selecionado == 'arthro_map':
                arthro_map.renderizar_ui()
            elif st.session_state.modulo_selecionado == 'nhfs':
                nhfs.renderizar_ui()
            elif st.session_state.modulo_selecionado == 'osteoporose':
                osteoporose.renderizar_ui()
            elif st.session_state.modulo_selecionado == 'start_back':
                start_back.renderizar_ui()
            elif st.session_state.modulo_selecionado == 'spine_sage':
                spine_sage.renderizar_ui()
            elif st.session_state.modulo_selecionado == 'rotator_cuff':
                rotator_cuff.renderizar_ui()
            elif st.session_state.modulo_selecionado == 'osteosarcoma':
                osteosarcoma.renderizar_ui()
            elif st.session_state.modulo_selecionado == 'foot_ankle_id':
                foot_ankle_id.renderizar_ui()
            elif st.session_state.modulo_selecionado == 'distal_radius':
                distal_radius.renderizar_ui()
            elif st.session_state.modulo_selecionado == 'distal_radius_instability':
                distal_radius_instability.renderizar_ui()
            elif st.session_state.modulo_selecionado == 'proximal_humerus_outcomes':
                proximal_humerus_outcomes.renderizar_ui()
                
            # Módulo de Relatório Oficial A4
            elif st.session_state.modulo_selecionado == 'relatorio':
                st.markdown("### 🖨️ Relatório Oficial (Formato A4)")
                linhas_html = ""
                df_rel_pac = obter_df_paciente(st.session_state.paciente_ativo['prontuario'])
                
                if not df_rel_pac.empty:
                    df_latest_rel = df_rel_pac.sort_values(by="Data/Hora").groupby("Avaliação Clínica").last().reset_index()
                    for _, r in df_latest_rel.iterrows():
                        param_str = r.get("Parâmetros Inseridos", "-")
                        linhas_html += f"""
                        <tr>
                            <td style="font-weight: bold; color: #1b5e20;">{r['Avaliação Clínica']}</td>
                            <td style="font-size: 12px; color: #555;">{param_str}</td>
                            <td style="font-weight: bold; text-align: center; color: #333;">{r['Resultado (%)']}%</td>
                            <td style="text-align: center; color: #333;">{r['Classificação']}</td>
                        </tr>
                        """
                
                html_relatorio = f"""
                <html>
                <head>
                <style>
                    body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background: transparent; margin: 0; padding: 20px; display: flex; justify-content: center; }}
                    .print-button {{ background: #1b5e20; color: white; border: none; padding: 12px 25px; border-radius: 8px; font-weight: bold; font-size: 16px; cursor: pointer; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 100%; }}
                    .a4-page {{ width: 210mm; min-height: 297mm; background: white; padding: 20mm; box-sizing: border-box; box-shadow: 0 10px 25px rgba(0,0,0,0.1); position: relative; color: black; }}
                    .header {{ border-bottom: 3px solid #1b5e20; padding-bottom: 15px; margin-bottom: 25px; text-align: center; }}
                    .header h1 {{ margin: 0; color: #1b5e20; font-size: 26px; text-transform: uppercase; }}
                    .header h3 {{ margin: 5px 0 0 0; color: #777; font-size: 14px; }}
                    .patient-box {{ background: #f8f9fa; border-left: 4px solid #1b5e20; padding: 15px 20px; margin-bottom: 30px; }}
                    table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
                    th, td {{ border-bottom: 1px solid #eee; padding: 14px 12px; font-size: 13px; }}
                    th {{ background-color: #1b5e20; color: white; text-align: center; text-transform: uppercase; font-size: 12px; }}
                    .footer {{ position: absolute; bottom: 20mm; left: 20mm; right: 20mm; border-top: 1px solid #ddd; padding-top: 15px; text-align: center; font-size: 11px; color: #777; }}
                    @media print {{ body {{ background: white; padding: 0; display: block; }} .no-print {{ display: none !important; }} .a4-page {{ width: 100%; height: auto; padding: 0; box-shadow: none; border: none; margin: 0; }} }}
                </style>
                </head>
                <body>
                    <div style="width: 210mm; max-width: 100%;">
                        <div class="no-print"><button class="print-button" onclick="window.print()">🖨️ CLIQUE AQUI PARA IMPRIMIR OU SALVAR EM PDF</button></div>
                        <div class="a4-page">
                            <div class="header">
                                <h1>Hospital Universitário Getúlio Vargas</h1>
                                <h3>OrtoPreditor Ilizarov - Relatório de Avaliação Preditiva</h3>
                            </div>
                            <div class="patient-box">
                                <p><b>Paciente:</b> {st.session_state.paciente_ativo['nome']}</p>
                                <p><b>Registro / Prontuário:</b> {st.session_state.paciente_ativo['prontuario']}</p>
                                <p><b>Nome da Mãe:</b> {st.session_state.paciente_ativo['mae']}</p>
                                <p><b>Data da Emissão:</b> {datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")}</p>
                            </div>
                            <table>
                                <tr><th style="width: 25%;">Módulo Clínico</th><th style="width: 45%;">Parâmetros</th><th style="width: 12%;">Resultado</th><th style="width: 18%;">Classificação</th></tr>
                                {linhas_html if linhas_html else '<tr><td colspan="4" style="text-align:center; padding: 20px;">Nenhuma avaliação realizada.</td></tr>'}
                            </table>
                            <div class="footer">
                                <p>OrtoPreditor Ilizarov • HUGV - UFAM</p>
                                <p>Made By Vinícius Bacelar Ferreira</p>
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                """
                components.html(html_relatorio, height=1200, scrolling=True)

# ==========================================
# GESTÃO & ANALYTICS (DASHBOARD)
# ==========================================
elif nav == "📊 Gestão & Analytics":
    st.title("📊 Painel de Analytics do Serviço (Orto)")
    df_g = obter_df_completo()
    
    if not df_g.empty:
        total_pacientes = df_g['Prontuário'].nunique()
        total_avaliacoes = len(df_g)
        col1, col2 = st.columns(2)
        col1.metric("Total de Pacientes", total_pacientes)
        col2.metric("Total de Avaliações", total_avaliacoes)
        
        st.markdown("---")
        st.subheader("🗃️ Base de Dados Completa")
        st.dataframe(df_g.sort_values(by="Data/Hora", ascending=False), use_container_width=True, hide_index=True)
    else: 
        st.info("Nenhum dado registrado na base de dados.")

st.markdown("<div class='watermark'>Made By Vinícius Bacelar Ferreira</div>", unsafe_allow_html=True)
