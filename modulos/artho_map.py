import streamlit as st
from utils import gerar_grafico_velocimetro, gerar_grafico_waterfall, obter_texto_explicativo
from database import salvar_registro

def calcular_risco(fc, perda_sangue, ureia, procedimento, raca, asa, comorbidade, fratura):
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

def renderizar_ui():
    st.markdown("<div class='calc-info'><b>O que calcula:</b> O modelo <b>Arthro-MAP</b> estratifica o risco de complicações major após artroplastia da anca e joelho durante o internamento.</div>", unsafe_allow_html=True)
    st.markdown("<div class='input-card'><h4>🦴 Arthro-MAP (Risco Pós-Operatório)</h4>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        fc = st.number_input("Menor Frequência Cardíaca (bpm):", min_value=0, max_value=200, value=60)
        sangue = st.number_input("Perda Sanguínea Estimada (mL):", min_value=0, max_value=5000, value=200, step=50)
        ureia = st.number_input("Ureia Sanguínea / BUN pré-operatória (mg/dL):", min_value=0, max_value=150, value=20)
    with c2:
        proc = st.selectbox("Tipo de Procedimento:", ["Primária", "Parcial", "Revisão"])
        asa = st.selectbox("Classificação ASA:", ["ASA <= 2 (I, II)", "ASA > 2 (III, IV, V)"])
        raca = st.selectbox("Raça do Paciente:", ["Não-Branco", "Branco"])
        comorbidade = st.selectbox("Principal Comorbidade Associada:", ["Nenhuma", "Pulmonar", "Cardiovascular", "Diabetes"])
        frat = st.toggle("Cirurgia motivada por fratura aguda?")
        
    if st.button("Calcular Risco Arthro-MAP", key="btn_arthro"):
        res, contribs = calcular_risco(fc, sangue, ureia, proc, raca, asa, comorbidade, frat)
        st.session_state.arthro_map_res = (res, contribs)
        salvar_registro("Arthro-MAP (Complicações)", res, "complicacao", f"FC: {fc} bpm | Sangue: {sangue}mL")
        
    if st.session_state.arthro_map_res:
        res, contribs = st.session_state.arthro_map_res
        col_g, col_x = st.columns([1, 1.5])
        with col_g: st.plotly_chart(gerar_grafico_velocimetro(res, "complicacao"), use_container_width=True)
        with col_x: 
            st.markdown("##### 🧠 Explicabilidade do Algoritmo (XAI)")
            st.markdown(obter_texto_explicativo(contribs))
            st.plotly_chart(gerar_grafico_waterfall(contribs, titulo="Impacto Variáveis (Arthro-MAP)"), use_container_width=True)
    
    with st.expander("📚 Referência Científica"):
        st.markdown("**Wuerz TH, Kent DM, Malchau H, Rubash HE.** A Nomogram to Predict Major Complications After Hip and Knee Arthroplasty. *The Journal of Arthroplasty*. 2014;29:1457-1462.")
    st.markdown("</div>", unsafe_allow_html=True)
