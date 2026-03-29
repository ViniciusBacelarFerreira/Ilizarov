import streamlit as st
from utils import gerar_grafico_velocimetro, gerar_grafico_waterfall, obter_texto_explicativo
from database import salvar_registro

def calcular_risco(idade, grau, t_stage, m_stage, cirurgia, quimioterapia, histologia):
    pontos = 0.0
    contribs = {}
    
    c_idade = 0
    if idade >= 60: c_idade = 15
    elif idade >= 40: c_idade = 8
    contribs["Idade Avançada"] = c_idade
    pontos += c_idade
    
    c_grau = 15 if grau == "Alto Grau (III-IV)" else 0
    contribs["Alto Grau Histológico"] = c_grau
    pontos += c_grau
    
    c_t = 0
    if t_stage == "T3 (Tumores descontínuos no osso primário)": c_t = 20
    elif t_stage == "T2 (> 8 cm na maior dimensão)": c_t = 10
    contribs["Estágio T Avançado"] = c_t
    pontos += c_t
    
    c_m = 35 if m_stage == "M1 (Metástase à distância)" else 0
    contribs["Presença de Metástase (M1)"] = c_m
    pontos += c_m
    
    c_cirurgia = 30 if cirurgia == "Não" else 0
    contribs["Ausência de Cirurgia"] = c_cirurgia
    pontos += c_cirurgia
    
    c_quimio = 20 if quimioterapia == "Não" else 0
    contribs["Ausência de Quimioterapia"] = c_quimio
    pontos += c_quimio
    
    c_hist = 5 if histologia not in ["Osteoblástico", "Condroblástico"] else 0
    contribs["Subtipo Histológico Desfavorável"] = c_hist
    pontos += c_hist
    
    prob = min(99.9, (pontos / 140.0) * 100)
    return round(prob, 1), contribs

def renderizar_ui():
    st.markdown("<div class='calc-info'><b>O que avalia:</b> Nomograma validado para estimar a <b>probabilidade de mortalidade câncer-específica (CSS) em 5 anos</b> em pacientes com osteossarcoma, utilizando dados demográficos, estadiamento tumoral e modalidades de tratamento.</div>", unsafe_allow_html=True)
    st.markdown("<div class='input-card'><h4>🎗️ Sobrevida no Osteossarcoma (Yu et al.)</h4>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Dados Clínicos e Histológicos")
        ost_idade = st.number_input("Idade do paciente (anos):", min_value=0, max_value=120, value=25)
        ost_hist = st.selectbox("Subtipo Histológico:", ["Osteoblástico", "Condroblástico", "Fibroblástico", "Telangiectásico", "Outro"])
        ost_grau = st.selectbox("Grau de Diferenciação:", ["Alto Grau (III-IV)", "Baixo Grau (I-II)"])
        
        st.markdown("##### Tratamento Recebido / Planejado")
        ost_cir = st.selectbox("Foi ou será submetido a ressecção cirúrgica do tumor primário?", ["Sim", "Não"])
        ost_quimio = st.selectbox("Recebeu ou receberá quimioterapia sistêmica?", ["Sim", "Não"])
        
    with c2:
        st.markdown("##### Estadiamento (Sistema TNM)")
        ost_t = st.selectbox("Estágio T (Tamanho do Tumor):", [
            "T1 (≤ 8 cm na maior dimensão)", 
            "T2 (> 8 cm na maior dimensão)", 
            "T3 (Tumores descontínuos no osso primário)"
        ])
        ost_m = st.selectbox("Estágio M (Metástase):", [
            "M0 (Sem metástase regional ou à distância)", 
            "M1 (Metástase à distância)"
        ])
        
    if st.button("Calcular Risco de Mortalidade Específica (5 Anos)", key="btn_osteo_sarcoma"):
        res, contribs = calcular_risco(ost_idade, ost_grau, ost_t, ost_m, ost_cir, ost_quimio, ost_hist)
        st.session_state.osteosarcoma_res = (res, contribs)
        params_str = f"Idade: {ost_idade} | {ost_t} | {ost_m} | Cirurgia: {ost_cir} | Quimio: {ost_quimio}"
        salvar_registro("Osteossarcoma (Mortalidade 5a)", res, "risco", params_str)
        
    if st.session_state.get('osteosarcoma_res'):
        res, contribs = st.session_state.osteosarcoma_res
        col_g, col_x = st.columns([1, 1.5])
        with col_g: 
            st.plotly_chart(gerar_grafico_velocimetro(res, "risco"), use_container_width=True)
        with col_x: 
            st.markdown("##### 🧠 Explicabilidade do Risco (XAI)")
            st.markdown(obter_texto_explicativo(contribs))
            st.plotly_chart(gerar_grafico_waterfall(contribs, titulo="Fatores Prognósticos Adversos"), use_container_width=True)
            
    with st.expander("📚 Referência Científica"):
        st.markdown("""
        **Yu Y, Wang S, Liu J, Ge J, Guan H.** Development and validation of a nomogram to predict long-term cancer-specific survival for patients with osteosarcoma. *Scientific Reports*. 2023;13:10230.  
        **DOI:** [10.1038/s41598-023-37391-8](https://doi.org/10.1038/s41598-023-37391-8)
        """)
    st.markdown("</div>", unsafe_allow_html=True)
