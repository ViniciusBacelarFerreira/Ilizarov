import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import datetime
import os
import sqlite3
import plotly.graph_objects as go
import math

# ==========================================
# CONFIGURAÇÃO INICIAL E ESTADO DA SESSÃO
# ==========================================
st.set_page_config(page_title="OrtoPreditor Ilizarov", layout="wide", page_icon="🦴")

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'paciente_ativo' not in st.session_state:
    st.session_state.paciente_ativo = {"nome": "", "mae": "", "prontuario": ""}

# Variáveis para armazenar o resultado atual na tela sem recarregar a página
lista_modulos = ['arthro_map_res', 'nhfs_res']
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
def gerar_grafico_waterfall(contribuicoes, titulo="Impacto das Variáveis"):
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
        decreasing={"marker":{"color":"#1b5e20"}}, increasing={"marker":{"color":"#ef6c00"}}, totals={"marker":{"color":"#333333"}}       
    ))
    fig.update_layout(title={"text": titulo, "font": {"size": 14}}, showlegend=False, height=320, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig

def gerar_grafico_velocimetro(prob, tipo="risco"):
    # Escala geral de probabilidade de complicação/mortalidade
    steps = [{'range': [0, 5], 'color': "rgba(46, 125, 50, 0.8)"}, 
             {'range': [5, 20], 'color': "rgba(239, 108, 0, 0.8)"}, 
             {'range': [20, 100], 'color': "rgba(198, 40, 40, 0.8)"}]
    title = "Risco Estimado"

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
# CÁLCULOS CLÍNICOS (ILIZAROV)
# ==========================================
def risco_complicacao_arthro_map(fc, perda_sangue, ureia, procedimento, raca, asa, comorbidade, fratura):
    """
    Arthro-MAP (Wuerz et al., 2014) - Risco de Complicação Maior em Artroplastias
    """
    pontos = 0.0
    contribs = {}

    c_fc = fc * (80.0 / 120.0) 
    contribs["Freq. Cardíaca"] = round(c_fc, 1)
    pontos += c_fc

    c_sangue = perda_sangue * (98.0 / 4000.0)
    contribs["Perda Sangue"] = round(c_sangue, 1)
    pontos += c_sangue

    c_ureia = ureia * (100.0 / 100.0)
    contribs["Ureia"] = round(c_ureia, 1)
    pontos += c_ureia

    c_proc = 0
    if procedimento == "Parcial": c_proc = 16
    elif procedimento == "Revisão": c_proc = 29
    contribs["Procedimento"] = c_proc
    pontos += c_proc

    c_raca = 28 if raca == "Branco" else 0
    contribs["Raça"] = c_raca
    pontos += c_raca

    c_asa = 29 if asa == "ASA > 2 (III, IV, V)" else 0
    contribs["ASA"] = c_asa
    pontos += c_asa

    c_com = 0
    if comorbidade == "Pulmonar": c_com = 16
    elif comorbidade == "Cardiovascular": c_com = 34
    elif comorbidade == "Diabetes": c_com = 38
    contribs["Comorbidades"] = c_com
    pontos += c_com

    c_frat = 65 if fratura else 0
    contribs["Fratura"] = c_frat
    pontos += c_frat

    if pontos <= 50: prob = 1.0
    elif pontos <= 100: prob = 5.0
    elif pontos <= 150: prob = 10.0 + ((pontos - 100) / 50) * 20.0 
    elif pontos <= 200: prob = 30.0 + ((pontos - 150) / 50) * 40.0 
    elif pontos <= 300: prob = 70.0 + ((pontos - 200) / 100) * 25.0 
    else: prob = 98.0

    return min(prob, 99.9), contribs

def risco_mortalidade_nhfs(idade, sexo, hb_baixa, amts_baixo, inst, comorb, malig):
    """
    Nottingham Hip Fracture Score (NHFS) - Mortalidade em 30 dias (Stanley et al., 2023) [cite: 639]
    """
    pontos = 0
    contribs = {}

    # Idade 
    if idade >= 86: p_idade = 4
    elif 66 <= idade <= 85: p_idade = 3
    else: p_idade = 0
    pontos += p_idade
    contribs["Idade"] = p_idade

    # Sexo 
    p_sexo = 1 if sexo == "Masculino" else 0
    pontos += p_sexo
    contribs["Sexo Masculino"] = p_sexo

    # Hemoglobina 
    p_hb = 1 if hb_baixa else 0
    pontos += p_hb
    contribs["Hb <= 10 g/dl"] = p_hb

    # Cognição (AMTS) 
    p_amts = 1 if amts_baixo else 0
    pontos += p_amts
    contribs["AMTS <= 6"] = p_amts

    # Institucionalizado 
    p_inst = 1 if inst else 0
    pontos += p_inst
    contribs["Vive em Instituição"] = p_inst

    # Comorbidades 
    p_comorb = 1 if comorb else 0
    pontos += p_comorb
    contribs[">= 2 Comorbidades"] = p_comorb

    # Malignidade 
    p_malig = 1 if malig else 0
    pontos += p_malig
    contribs["Malignidade"] = p_malig

    # Fórmula 
    prob = 100.0 / (1.0 + math.exp(4.718 - (pontos / 2.0)))

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
        st.markdown("<p style='text-align: center; font-size: 1.15rem; opacity: 0.85; max-width: 900px; margin: 15px auto 35px auto;'>Sistema de apoio à decisão cirúrgica em Ortopedia e Traumatologia. Utiliza modelos preditivos baseados na literatura médica para estimar riscos de complicações e mortalidade.</p>", unsafe_allow_html=True)
        
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
        
        tabs = st.tabs(["📊 Painel Visual", "🦴 Artroplastia (Arthro-MAP)", "🩼 Fratura de Fêmur (NHFS)", "📄 Relatório Oficial"])

        painel_placeholder = tabs[0].empty()
        relatorio_placeholder = tabs[3].empty()

        with tabs[1]: 
            st.markdown("<div class='calc-info'><b>O que calcula:</b> O modelo <b>Arthro-MAP</b> estratifica o risco de complicações maiores após artroplastia de quadril e joelho durante a internação.</div>", unsafe_allow_html=True)
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
                    st.plotly_chart(gerar_grafico_waterfall(contribs, titulo="Impacto das Variáveis (Arthro-MAP)"), use_container_width=True)
                
            with st.expander("📚 Referência Científica"):
                st.markdown("""
                **Wuerz TH, Kent DM, Malchau H, Rubash HE.** A Nomogram to Predict Major Complications After Hip and Knee Arthroplasty. *The Journal of Arthroplasty*. 2014;29:1457-1462.
                """)
            st.markdown("</div>", unsafe_allow_html=True)

        with tabs[2]: 
            st.markdown("<div class='calc-info'><b>O que calcula:</b> O <b>Nottingham Hip Fracture Score (NHFS)</b> prediz a probabilidade de <b>mortalidade em 30 dias</b> em pacientes com fratura do fêmur proximal, utilizando dados de admissão.</div>", unsafe_allow_html=True)
            st.markdown("<div class='input-card'><h4>🩼 NHFS (Risco de Mortalidade)</h4>", unsafe_allow_html=True)
            
            n1, n2 = st.columns(2)
            with n1:
                nhfs_idade = st.number_input("Idade do paciente (anos):", min_value=0, max_value=120, value=75)
                nhfs_sexo = st.selectbox("Sexo biológico:", ["Feminino", "Masculino"])
                nhfs_hb = st.toggle("Hemoglobina de admissão ≤ 10 g/dl?")
                nhfs_amts = st.toggle("Escore Cognitivo AMTS ≤ 6 (ou diagnóstico de demência)?")
                
            with n2:
                nhfs_inst = st.toggle("O paciente reside em instituição de longa permanência (asilo)?")
                nhfs_comorb = st.toggle("O paciente possui 2 ou mais comorbidades sistêmicas?")
                nhfs_malig = st.toggle("O paciente possui diagnóstico de malignidade (câncer)?")
            
            if st.button("Calcular e Salvar Risco de Mortalidade (NHFS)", key="btn_nhfs"):
                res, contribs = risco_mortalidade_nhfs(nhfs_idade, nhfs_sexo, nhfs_hb, nhfs_amts, nhfs_inst, nhfs_comorb, nhfs_malig)
                params = f"Idade: {nhfs_idade} | Sexo: {nhfs_sexo} | Hb≤10: {'Sim' if nhfs_hb else 'Não'} | AMTS≤6: {'Sim' if nhfs_amts else 'Não'} | Inst: {'Sim' if nhfs_inst else 'Não'} | ≥2 Comorb: {'Sim' if nhfs_comorb else 'Não'} | Malig: {'Sim' if nhfs_malig else 'Não'}"
                st.session_state.nhfs_res = (res, contribs)
                salvar_registro("NHFS (Mortalidade 30d)", res, "risco", params)
            
            if st.session_state.nhfs_res is not None:
                res, contribs = st.session_state.nhfs_res
                st.success("Cálculo realizado e salvo com sucesso na base de dados!")
                
                col_g, col_x = st.columns([1, 1.5])
                with col_g:
                    st.plotly_chart(gerar_grafico_velocimetro(res, "risco"), use_container_width=True)
                with col_x:
                    st.markdown("##### 🧠 Explicabilidade do Algoritmo (XAI)")
                    st.markdown(obter_texto_explicativo(contribs))
                    st.plotly_chart(gerar_grafico_waterfall(contribs, titulo="Impacto das Variáveis (NHFS)"), use_container_width=True)
                
            with st.expander("📚 Referência Científica"):
                st.markdown("""
                **Stanley C, Lennon D, Moran C, Vasireddy A, Rowan F.** Risk scoring models for patients with proximal femur fractures: Qualitative systematic review assessing 30-day mortality and ease of use. *Injury*. 2023;54:111017. [cite: 338-339]  
                **DOI:** [10.1016/j.injury.2023.111017](https://doi.org/10.1016/j.injury.2023.111017)
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
                st.info("Nenhum cálculo salvo ainda. Realize a avaliação nas abas clínicas.")
                    
        with relatorio_placeholder.container():
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
