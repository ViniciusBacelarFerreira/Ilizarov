import streamlit as st
from utils import gerar_grafico_velocimetro, gerar_grafico_waterfall, obter_texto_explicativo
from database import salvar_registro

def calcular_risco(idade, sexo, bmi, copd, card, renal, has, dm, malig, ra, urgencia, sii):
    # Cálculo proxy estruturado com base nas variáveis do SpineSage (validadas por Coia et al., 2022)
    pontos = 0.0
    contribs = {}
    
    # Idade
    c_idade = (idade - 50) * 0.2 if idade > 50 else 0
    contribs["Idade"] = round(c_idade, 1)
    pontos += c_idade
    
    # BMI
    c_bmi = (bmi - 25) * 0.3 if bmi > 25 else 0
    contribs["IMC"] = round(c_bmi, 1)
    pontos += c_bmi
    
    # Comorbidades
    c_copd = 5.0 if copd else 0
    contribs["DPOC"] = c_copd; pontos += c_copd
    
    c_card = 6.0 if card else 0
    contribs["Cardiopatia"] = c_card; pontos += c_card
    
    c_renal = 7.0 if renal else 0
    contribs["Doença Renal"] = c_renal; pontos += c_renal
    
    c_has = 3.0 if has else 0
    contribs["Hipertensão"] = c_has; pontos += c_has
    
    c_dm = 4.0 if dm else 0
    contribs["Diabetes"] = c_dm; pontos += c_dm
    
    c_malig = 8.0 if malig else 0
    contribs["Malignidade"] = c_malig; pontos += c_malig
    
    c_ra = 4.0 if ra else 0
    contribs["Artrite Reumatoide"] = c_ra; pontos += c_ra
    
    # Fatores Cirúrgicos
    c_urg = 5.0 if urgencia else 0
    contribs["Emergência"] = c_urg; pontos += c_urg
    
    c_sii = sii * 1.5
    contribs["Índice Invasividade (SII)"] = round(c_sii, 1)
    pontos += c_sii
    
    # Normalização simplificada para percentagem de risco
    prob = min(99.9, pontos * 0.8) 
    
    return round(prob, 1), contribs

def renderizar_ui():
    st.markdown("<div class='calc-info'><b>O que avalia:</b> O modelo <b>SpineSage</b> demonstrou a maior precisão (AUC 0.75) para predizer complicações aos 30 dias após cirurgia da coluna vertebral. <i>Nota: O cálculo reflete uma ponderação proxy baseada nas variáveis originais validadas clinicamente.</i></div>", unsafe_allow_html=True)
    st.markdown("<div class='input-card'><h4>🦴 SpineSage (Complicações na Coluna)</h4>", unsafe_allow_html=True)
    
    s1, s2 = st.columns(2)
    with s1:
        st.markdown("##### Dados Demográficos")
        ss_idade = st.number_input("Idade do paciente (anos):", min_value=0, max_value=120, value=60)
        ss_sexo = st.selectbox("Sexo biológico:", ["Feminino", "Masculino"], key="ss_sexo")
        ss_bmi = st.number_input("Índice de Massa Corporal (IMC):", min_value=10.0, max_value=60.0, value=25.0)
        
        st.markdown("##### Fatores Cirúrgicos")
        ss_urg = st.toggle("Cirurgia de Emergência?")
        ss_sii = st.number_input("Surgical Invasiveness Index (SII):", min_value=0, max_value=50, value=6, help="Ex: Descompressão simples = 1-2; Fusão multinível = 7-12+")
        
    with s2:
        st.markdown("##### Comorbidades")
        ss_copd = st.toggle("DPOC (Doença Pulmonar Obstrutiva Crónica)?")
        ss_card = st.toggle("Disfunção Cardíaca (Insuficiência ou complicação prévia)?")
        ss_renal = st.toggle("Disfunção Renal?")
        ss_has = st.toggle("Hipertensão Arterial?")
        ss_dm = st.toggle("Diabetes Mellitus?")
        ss_malig = st.toggle("Malignidade (Cancro)?")
        ss_ra = st.toggle("Artrite Reumatoide?")
        
    if st.button("Calcular Risco de Complicação (SpineSage)", key="btn_spinesage"):
        res, contribs = calcular_risco(ss_idade, ss_sexo, ss_bmi, ss_copd, ss_card, ss_renal, ss_has, ss_dm, ss_malig, ss_ra, ss_urg, ss_sii)
        st.session_state.spinesage_res = (res, contribs)
        params_str = f"Idade: {ss_idade} | IMC: {ss_bmi} | SII: {ss_sii}"
        salvar_registro("SpineSage (Coluna)", res, "complicacao", params_str)
        
    if st.session_state.get('spinesage_res'):
        res, contribs = st.session_state.spinesage_res
        col_g, col_x = st.columns([1, 1.5])
        with col_g: 
            st.plotly_chart(gerar_grafico_velocimetro(res, "complicacao"), use_container_width=True)
        with col_x: 
            st.markdown("##### 🧠 Explicabilidade do Algoritmo (XAI)")
            st.markdown(obter_texto_explicativo(contribs))
            st.plotly_chart(gerar_grafico_waterfall(contribs, titulo="Impacto das Variáveis (SpineSage)"), use_container_width=True)
            
    with st.expander("📚 Referência Científica"):
        st.markdown("""
        **Coia M, Baker JF.** Predicting complications of spine surgery: external validation of three models. *The Spine Journal*. 2022;22(11):1801-1810.  
        **DOI:** [10.1016/j.spinee.2022.07.092](https://doi.org/10.1016/j.spinee.2022.07.092)
        """)
    st.markdown("</div>", unsafe_allow_html=True)
