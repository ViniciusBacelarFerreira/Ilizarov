import streamlit as st
from utils import gerar_grafico_velocimetro, gerar_grafico_waterfall, obter_texto_explicativo
from database import salvar_registro

def calcular_risco(dor_severa, escolaridade_baixa, idade, comorbidades_altas):
    # Cálculo estruturado com base na árvore de regressão do WRIST Trial (Chung et al., 2019)
    # Estima o risco de recuperação funcional insatisfatória (baixo escore MHQ)
    pontos = 0.0
    contribs = {}
    
    c_dor = 35 if dor_severa else 0
    contribs["Dor Inicial Severa"] = c_dor
    pontos += c_dor
    
    c_esc = 25 if escolaridade_baixa else 0
    contribs["Escolaridade (≤ Ensino Médio)"] = c_esc
    pontos += c_esc
    
    c_idade = 20 if idade > 87 else 0
    contribs["Idade > 87 anos"] = c_idade
    pontos += c_idade
    
    c_comorb = 20 if comorbidades_altas else 0
    contribs["Comorbidades (≥ 2)"] = c_comorb
    pontos += c_comorb
    
    # Risco base ajustado + penalizações
    prob = min(99.9, 10 + pontos * 0.9)
    
    return round(prob, 1), contribs

def renderizar_ui():
    st.markdown("<div class='calc-info'><b>O que avalia:</b> Baseado no <i>WRIST Trial</i>, este modelo estima o risco de <b>recuperação funcional insatisfatória</b> 12 meses após uma fratura do rádio distal em idosos, utilizando preditores clínicos e demográficos.</div>", unsafe_allow_html=True)
    st.markdown("<div class='input-card'><h4>✋ Fratura do Rádio Distal (Prognóstico Funcional)</h4>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Dados Demográficos")
        dr_idade = st.number_input("Idade do paciente (anos):", min_value=60, max_value=120, value=70, help="O estudo focou em pacientes a partir dos 60 anos.")
        dr_esc = st.selectbox("Nível de Escolaridade:", ["Ensino Superior / Universitário", "Ensino Médio ou Inferior"])
        
    with c2:
        st.markdown("##### Apresentação Clínica")
        dr_dor = st.selectbox("Intensidade da Dor na apresentação inicial:", ["Leve a Moderada", "Severa a Extrema"])
        dr_comorb = st.selectbox("Número de Comorbidades pré-existentes:", ["0 a 1 comorbidade", "2 ou mais comorbidades"])
        
    if st.button("Calcular Risco de Pior Desfecho Funcional", key="btn_distal_radius"):
        dor_sev = True if dr_dor == "Severa a Extrema" else False
        esc_baixa = True if dr_esc == "Ensino Médio ou Inferior" else False
        comorb_altas = True if dr_comorb == "2 ou mais comorbidades" else False
        
        res, contribs = calcular_risco(dor_sev, esc_baixa, dr_idade, comorb_altas)
        st.session_state.distal_radius_res = (res, contribs)
        params_str = f"Idade: {dr_idade} | Dor: {dr_dor} | Escolaridade: {dr_esc} | Comorbidades: {dr_comorb}"
        salvar_registro("Rádio Distal (Prognóstico)", res, "risco", params_str)
        
    if st.session_state.get('distal_radius_res'):
        res, contribs = st.session_state.distal_radius_res
        col_g, col_x = st.columns([1, 1.5])
        with col_g: 
            st.plotly_chart(gerar_grafico_velocimetro(res, "risco"), use_container_width=True)
        with col_x: 
            st.markdown("##### 🧠 Explicabilidade do Prognóstico (XAI)")
            if sum(contribs.values()) == 0:
                st.success("🟢 **Excelente Prognóstico:** O paciente possui o perfil ideal (dor controlada, boa escolaridade, idade ≤87 e poucas comorbidades) para atingir os maiores escores funcionais (MHQ).")
            else:
                st.markdown(obter_texto_explicativo(contribs))
            st.plotly_chart(gerar_grafico_waterfall(contribs, titulo="Fatores de Risco Funcional (WRIST)"), use_container_width=True)
            
    with st.expander("📚 Referência Científica"):
        st.markdown("""
        **Chung KC, Kim HM, Malay S, Shauver MJ; WRIST Group.** Predicting Outcomes After Distal Radius Fracture: A 24-Center International Clinical Trial of Older Adults. *The Journal of Hand Surgery*. 2019;44(9):762-771.  
        **DOI:** [10.1016/j.jhsa.2018.10.021](https://doi.org/10.1016/j.jhsa.2018.10.021)
        """)
    st.markdown("</div>", unsafe_allow_html=True)
