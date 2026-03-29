import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import datetime
import os
import sqlite3
import plotly.graph_objects as go

# ==========================================
# CONFIGURAÇÃO INICIAL E ESTADO DA SESSÃO
# ==========================================
st.set_page_config(page_title="OrtoPreditor Ilizarov", layout="wide", page_icon="🦴")

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'paciente_ativo' not in st.session_state:
    st.session_state.paciente_ativo = {"nome": "", "mae": "", "prontuario": ""}

# Variáveis para armazenar o resultado atual na tela sem recarregar a página
lista_modulos = ['arthro_map_res']
for mod in lista_modulos:
    if mod not in st.session_state:
        st.session_state[mod] = None

DB_NAME = "ilizarov_database.db"
SENHA_CORRETA = "hugv1869"

# ==========================================
# INICIALIZAÇÃO DA BASE DE DADOS (SQLITE)
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS avaliacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT,
            prontuario TEXT,
            paciente TEXT,
            mae TEXT,
            avaliacao_clinica TEXT,
            parametros TEXT,
            resultado REAL,
            classificacao TEXT,
            tipo TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# FUNÇÕES DE XAI E GRÁFICOS
# ==========================================
def gerar_grafico_waterfall(contribuicoes, titulo="Impacto das Variáveis (Arthro-MAP)"):
    labels = list(contribuicoes.keys())
    values = list(contribuicoes.values())
    
    measures = ["relative"] * len(labels)
    labels.append("Pontuação Total")
    values.append(sum(values))
    measures.append("total")
    
    fig = go.Figure(go.Waterfall(
        orientation="v", measure=measures, x=labels, textposition="outside",
        text=[f"{v:+.1f}" if m == "relative" else f"{v:.1f}" for m, v in zip(measures, values)],
        y=values, connector={"line":{"color":"rgba(128,128,128,0.5)"}},
        decreasing={"marker":{"color":"#1565c0"}}, increasing={"marker":{"color":"#ef6c00"}}, totals={"marker":{"color":"#333333"}}       
    ))
    fig.update_layout(title={"text": titulo, "font": {"size": 14}}, showlegend=False, height=320, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig

def gerar_grafico_velocimetro(prob, tipo="risco"):
    # Adaptado para a escala de probabilidade de complicação
    steps = [{'range': [0, 5], 'color': "rgba(46, 125, 50, 0.8)"}, 
             {'range': [5, 20], 'color': "rgba(239, 108, 0, 0.8)"}, 
             {'range': [20, 100], 'color': "rgba(198, 40, 40, 0.8)"}]
    title = "Risco de Complicação"

    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=prob, number={'suffix': "%", 'font': {'size': 40, 'color': '#333'}},
        domain={'x': [0, 1], 'y': [0, 1]}, title={'text': title, 'font': {'size': 18, 'color': '#555'}},
        gauge={'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"}, 'bar': {'color': "rgba(0, 0, 0, 0.8)", 'thickness': 0.15}, 'bgcolor': "white", 'borderwidth': 2, 'bordercolor': "gray", 'steps': steps}
    ))
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor='rgba(0,0,0,0)')
    return fig

def obter_texto_explicativo(contribuicoes):
    contribs_clinicas = {k: v for k, v in contribuicoes.items()}
    if not contribs_clinicas: return ""
    max_var = max(contribs_clinicas, key=lambda k: contribs_clinicas[k])
    max_val = contribs_clinicas[max_var]
    if max_val == 0: return "Nenhum fator de risco adicional pontuou neste paciente."
    return f"A variável que mais **aumentou** a pontuação de risco neste paciente foi: **{max_var}** (+{max_val:.1f} pontos)."

# ==========================================
# CÁLCULOS CLÍNICOS (ILIZAROV - ARTHRO-MAP)
# ==========================================
def risco_complicacao_arthro_map(fc, perda_sangue, ureia, procedimento, raca, asa, comorbidade, fratura):
    """
    Baseado no nomograma Arthro-MAP (Wuerz et al., 2014)
    Calcula pontos baseados na Figura 1 e interpola probabilidade.
    """
    pontos = 0.0
    contribs = {}

    # Variáveis Contínuas (Interpolação linear da escala visual Fig. 1)
    c_fc = fc * (80.0 / 120.0) 
    contribs["Frequência Cardíaca"] = round(c_fc, 1)
    pontos += c_fc

    c_sangue = perda_sangue * (98.0 / 4000.0)
    contribs["Perda Sanguínea"] = round(c_sangue, 1)
    pontos += c_sangue

    c_ureia = ureia * (100.0 / 100.0)
    contribs["Ureia (BUN)"] = round(c_ureia, 1)
    pontos += c_ureia

    # Procedimento
    c_proc = 0
    if procedimento == "Parcial": c_proc = 16
    elif procedimento == "Revisão": c_proc = 29
    contribs["Procedimento"] = c_proc
    pontos += c_proc

    # Raça
    c_raca = 28 if raca == "Branco" else 0
    contribs["Raça"] = c_raca
    pontos += c_raca

    # ASA
    c_asa = 29 if asa == "ASA > 2 (III, IV, V)" else 0
    contribs["Escore ASA"] = c_asa
    pontos += c_asa

    # Comorbidades
    c_com = 0
    if comorbidade == "Pulmonar": c_com = 16
    elif comorbidade == "Cardiovascular": c_com = 34
    elif comorbidade == "Diabetes": c_com = 38
    contribs["Comorbidades"] = c_com
    pontos += c_com

    # Fratura
    c_frat = 65 if fratura else 0
    contribs["Fratura"] = c_frat
    pontos += c_frat

    # Interpolação de Probabilidade (Eixo inferior Fig. 1)
    # Aproximação da curva de calibração
    if pontos <= 50: prob = 1.0
    elif pontos <= 100: prob = 5.0
    elif pontos <= 150: prob = 10.0 + ((pontos - 100) / 50) * 20.0 # Até 30%
    elif pontos <= 200: prob = 30.0 + ((pontos - 150) / 50) * 40.0 # Até 70%
    elif pontos <= 300: prob = 70.0 + ((pontos - 200) / 100) * 25.0 # Até 95%
    else: prob = 98.0

    return min(prob, 99.9), contribs

# ==========================================
# GESTÃO DE DADOS (SQLITE)
# ==========================================
def obter_classificacao(prob, tipo):
    if prob < 5: return ("Baixo Risco", "green")
    elif prob < 20: return ("Risco Moderado", "orange")
    else: return ("Alto Risco", "red")

def salvar_registro(mod, prob, tipo, parametros=""):
    pac = st.session_state.paciente_ativo['nome']
    mae = st.session_state.paciente_ativo['mae']
    pront = str(st.session_state.paciente_ativo['prontuario'])
    classif, _ = obter_classificacao(prob, tipo)
    data = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO avaliacoes (data_hora, prontuario, paciente, mae, avaliacao_clinica, parametros, resultado, classificacao, tipo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (data, pront, pac, mae, mod, parametros, round(prob, 1), classif, tipo))
    conn.commit()
    conn.close()
    return True

def obter_df_paciente(prontuario):
    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT data_hora as "Data/Hora", avaliacao_clinica as "Avaliação Clínica", parametros as "Parâmetros Inseridos", 
               resultado as "Resultado (%)", classificacao as "Classificação", tipo as "Tipo"
        FROM avaliacoes WHERE prontuario = ?
    '''
    df = pd.read_sql(query, conn, params=(str(prontuario),))
    conn.close()
    return df

def obter_df_completo():
    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT data_hora as "Data/Hora", prontuario as "Prontuário", paciente as "Paciente", mae as "Mãe",
               avaliacao_clinica as "Avaliação Clínica", parametros as "Parâmetros Inseridos", 
               resultado as "Resultado (%)", classificacao as "Classificação", tipo as "Tipo"
        FROM avaliacoes
    '''
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# ==========================================
# ESTILOS CSS INTELIGENTES 
# ==========================================
st.markdown("""
<style>
    .login-box { background-color: var(--secondary-background-color); border-radius: 24px; border: 1px solid rgba(128, 128, 128, 0.15); padding: 50px; box-shadow: 0 15px 35px rgba(0, 0, 0, 0.15); text-align: center; max-width: 500px; margin: auto; color: var(--text-color); }
    .watermark { position: fixed; bottom: 20px; right: 30px; opacity: 0.5; font-family: 'Georgia', serif; font-style: italic; font-size: 0.9rem; pointer-events: none; color: var(--text-color); }
    .main-title { background: -webkit-linear-gradient(45deg, #1b5e20, #4caf50); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; font-size: 3.5rem; text-align: center; letter-spacing: -1px; }
    .ilizarov-text { font-family: 'Georgia', serif; font-style: italic; color: #4caf50; margin-left: 10px; }
    .patient-header { background: linear-gradient(135deg, #1b5e20, #4caf50); color: white; padding: 25px 35px; border-radius: 20px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 10px 30px rgba(27, 94, 32, 0.2); }
    .dashboard-card { background-color: var(--secondary-background-color); border-radius: 16px; padding: 24px; box-shadow: 0 8px 24px rgba(0,0,0,0.06); text-align: left; border-left: 8px solid #ddd; color: var(--text-color); transition: all 0.3s ease; display: flex; flex-direction: column; justify-content: space-between; }
    .dashboard-card:hover { transform: translateY(-4px); box-shadow: 0 12px 32px rgba(0,0,0,0.1); }
    .card-value { font-size: 2.5rem; font-weight: 800; margin: 10px 0; line-height: 1; }
    .b-green { border-left-color: #2e7d32 !important; } .t-green { color: #2e7d32 !important; }
    .b-orange { border-left-color: #ef6c00 !important; } .t-orange { color: #ef6c00 !important; }
    .b-red { border-left-color: #c62828 !important; } .t-red { color: #c62828 !important; }
    .input-card { background-color: var(--secondary-background-color); padding: 35px; border-radius: 20px; box-shadow: 0 8px 30px rgba(0,0,0,0.05); margin-top: 15px; color: var(--text-color); border: 1px solid rgba(128, 128, 128, 0.1); }
    .calc-info { background-color: rgba(76, 175, 80, 0.05); padding: 16px 20px; border-radius: 12px; border-left: 5px solid #4caf50; margin-bottom: 25px; font-size: 0.95rem; color: var(--text-color); box-shadow: 0 2px 10px rgba(0,0,0,0.02); }
    .sidebar-section-title { font-size: 0.75rem; font-weight: 700; color: #888; text-transform: uppercase; letter-spacing: 1.2px; margin-top: 20px; margin-bottom: 10px; }
    .sidebar-patient-card { background: rgba(76, 175, 80, 0.08); border-left: 4px solid #4caf50; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

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
            for mod in lista_modulos:
                st.session_state[mod] = None
            st.rerun()
        st.markdown("<hr style='margin: 15px 0; opacity: 0.2;'>", unsafe_allow_html=True)

    if st.button("🚪 Sair do Sistema", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.paciente_ativo = {"nome": "", "mae": "", "prontuario": ""}
        st.rerun()
        
    st.markdown("<br><br><p style='text-align: center; font-size: 0.75rem; font-weight: bold; opacity: 0.5;'>Made By Vinícius Bacelar Ferreira</p>", unsafe_allow_html=True)

# ==========================================
# ÁREA DE TRABALHO
# ==========================================
if nav == "🏠 Área de Trabalho":
    if not st.session_state.paciente_ativo['prontuario']:
        st.markdown("<h1 class='main-title'>OrtoPreditor <span class='ilizarov-text'>Ilizarov</span></h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 1.15rem; opacity: 0.85; max-width: 900px; margin: 15px auto 35px auto;'>Sistema de apoio à decisão cirúrgica em Ortopedia e Traumatologia. Utiliza modelos preditivos para estimar riscos de complicações pós-operatórias baseados em dados pré e intraoperatórios.</p>", unsafe_allow_html=True)
        
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
                        st.rerun()
                else:
                    st.warning("Nenhum paciente encontrado.")
            else: 
                st.info("Sem registros na base de dados no momento.")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with c2:
            st.markdown("<div class='input-card'><h3>➕ Cadastrar Novo Paciente</h3>", unsafe_allow_html=True)
            nn = st.text_input("Nome Completo do Paciente:")
            nm = st.text_input("Nome da Mãe:")
            np = st.text_input("Número do Prontuário:")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Cadastrar e Iniciar Atendimento", use_container_width=True) and nn and np:
                st.session_state.paciente_ativo = {"nome": nn, "mae": nm, "prontuario": str(np)}
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
        
        tabs = st.tabs(["📊 Painel Visual", "🦴 Artroplastia (Arthro-MAP)", "📄 Relatório Oficial"])

        painel_placeholder = tabs[0].empty()
        relatorio_placeholder = tabs[2].empty()

        with tabs[1]: 
            st.markdown("<div class='calc-info'><b>O que calcula:</b> O modelo <b>Arthro-MAP</b> estratifica o risco de complicações maiores após artroplastia de quadril e joelho (ex: IAM, TEP, falência renal, infecção profunda) durante a internação.</div>", unsafe_allow_html=True)
            st.markdown("<div class='input-card'><h4>🦴 Arthro-MAP (Risco Pós-Operatório)</h4>", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("##### Variáveis Intraoperatórias")
                fc = st.number_input("Menor Frequência Cardíaca (bpm):", min_value=0, max_value=200, value=60)
                sangue = st.number_input("Perda Sanguínea Estimada (mL):", min_value=0, max_value=5000, value=200, step=50)
                
                st.markdown("##### Variáveis Laboratoriais")
                ureia = st.number_input("Ureia Sanguínea / BUN pré-operatória (mg/dL):", min_value=0, max_value=150, value=20)
                
            with c2:
                st.markdown("##### Variáveis Pré-operatórias Clínicas")
                proc = st.selectbox("Tipo de Procedimento:", ["Primária", "Parcial", "Revisão"])
                asa = st.selectbox("Classificação ASA:", ["ASA <= 2 (I, II)", "ASA > 2 (III, IV, V)"])
                raca = st.selectbox("Raça do Paciente:", ["Não-Branco", "Branco"])
                
                comorbidade = st.selectbox("Principal Comorbidade Associada:", ["Nenhuma", "Pulmonar", "Cardiovascular", "Diabetes"])
                frat = st.toggle("Cirurgia motivada por fratura aguda?")
            
            if st.button("Calcular e Salvar Risco Arthro-MAP", key="btn_arthro"):
                res, contribs = risco_complicacao_arthro_map(fc, sangue, ureia, proc, raca, asa, comorbidade, frat)
                params = f"FC: {fc} bpm | Sangue: {sangue}mL | Ureia: {ureia} | {proc} | {asa} | Comorb: {comorbidade} | Fratura: {'Sim' if frat else 'Não'}"
                st.session_state.arthro_map_res = (res, contribs)
                salvar_registro("Arthro-MAP (Complicações)", res, "risco", params)
            
            if st.session_state.arthro_map_res is not None:
                res, contribs = st.session_state.arthro_map_res
                st.success("Cálculo realizado e salvo com sucesso na base de dados!")
                
                col_g, col_x = st.columns([1, 1.5])
                with col_g:
                    st.plotly_chart(gerar_grafico_velocimetro(res, "risco"), use_container_width=True)
                with col_x:
                    st.markdown("##### 🧠 Explicabilidade do Algoritmo (XAI)")
                    st.markdown(obter_texto_explicativo(contribs))
                    st.plotly_chart(gerar_grafico_waterfall(contribs), use_container_width=True)
                
            with st.expander("📚 Referência Científica"):
                st.markdown("""
                **Wuerz TH, Kent DM, Malchau H, Rubash HE.** A Nomogram to Predict Major Complications After Hip and Knee Arthroplasty. *The Journal of Arthroplasty*. 2014;29:1457-1462.  
                **DOI:** [10.1016/j.arth.2013.09.007](http://dx.doi.org/10.1016/j.arth.2013.09.007)
                """)
            st.markdown("</div>", unsafe_allow_html=True)

        # =======================================================
        # PREENCHIMENTO DOS PLACEHOLDERS (PAINEL E RELATÓRIO)
        # =======================================================
        with painel_placeholder.container():
            st.subheader("📊 Resultados Consolidados e Arquivados")
            df_p = obter_df_paciente(st.session_state.paciente_ativo['prontuario'])
            if not df_p.empty:
                df_l = df_p.sort_values(by="Data/Hora").groupby("Avaliação Clínica").last().reset_index()
                cols = st.columns(3)
                for
