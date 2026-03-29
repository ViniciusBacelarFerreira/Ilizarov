import streamlit as st
import math
from utils import gerar_grafico_velocimetro, gerar_grafico_waterfall, obter_texto_explicativo
from database import salvar_registro

def calcular_risco(idade, sexo, hb_baixa, amts_baixo, inst, comorb, malig):
    pontos = 0
    contribs = {}
    
    if idade >= 86: p_idade = 4
    elif 66 <= idade <= 85: p_idade = 3
    else: p_idade = 0
    pontos += p_idade; contribs["Idade"] = p_idade
    
    p_sexo = 1 if sexo == "Masculino" else 0
    pontos += p_sexo; contribs["Sexo Masculino"] = p_sexo
    
    p_hb = 1 if hb_baixa else 0
    pontos += p_hb; contribs["Hb <= 10 g/dl"] = p_hb
    
    p_amts = 1 if amts_baixo else 0
    pontos += p_amts; contribs["AMTS <= 6"] = p_amts
    
    p_inst = 1 if inst else 0
    pontos += p_inst; contribs["Vive em Instituição"] = p_inst
    
    p_comorb = 1 if comorb else 0
    pontos += p_comorb; contribs[">= 2 Comorbidades"] = p_comorb
    
    p_malig = 1 if malig else 0
    pontos += p_malig; contribs["Malignidade"] = p_malig

    prob = 100.0 / (1.0 + math.exp(4.718 - (pontos / 2.0)))
    return min(prob, 99.9), contribs

def renderizar_ui():
    st.markdown("<div class='calc-info'><b>O que calcula:</b> O <b>Nottingham Hip Fracture Score (NHFS)</b> prediz a probabilidade de <b>mortalidade em 30 dias</b> em pacientes com fratura do fêmur proximal.</div>", unsafe_allow_html=True)
    # (...)
        nhfs_malig = st.toggle("O paciente possui diagnóstico de malignidade (câncer)?")

    with n1:
        nhfs_idade = st.number_input("Idade do paciente (anos):", min_value=0, max_value=120, value=75)
        nhfs_sexo = st.selectbox("Sexo biológico:", ["Feminino", "Masculino"])
        nhfs_hb = st.toggle("Hemoglobina de admissão ≤ 10 g/dl?")
        nhfs_amts = st.toggle("Escore Cognitivo AMTS ≤ 6 (ou diagnóstico de demência)?")
    with n2:
        nhfs_inst = st.toggle("O paciente reside em instituição de longa permanência (lar)?")
        nhfs_comorb = st.toggle("O paciente possui 2 ou mais comorbidades sistémicas?")
        nhfs_malig = st.toggle("O paciente possui diagnóstico de malignidade (cancro)?")
        
    if st.button("Calcular Risco de Mortalidade (NHFS)", key="btn_nhfs"):
        res, contribs = calcular_risco(nhfs_idade, nhfs_sexo, nhfs_hb, nhfs_amts, nhfs_inst, nhfs_comorb, nhfs_malig)
        st.session_state.nhfs_res = (res, contribs)
        salvar_registro("NHFS (Mortalidade 30d)", res, "risco", f"Idade: {nhfs_idade} | Hb≤10: {nhfs_hb}")
        
    if st.session_state.nhfs_res:
        res, contribs = st.session_state.nhfs_res
        col_g, col_x = st.columns([1, 1.5])
        with col_g: st.plotly_chart(gerar_grafico_velocimetro(res, "risco"), use_container_width=True)
        with col_x: 
            st.markdown("##### 🧠 Explicabilidade do Algoritmo (XAI)")
            st.markdown(obter_texto_explicativo(contribs))
            st.plotly_chart(gerar_grafico_waterfall(contribs, titulo="Impacto das Variáveis (NHFS)"), use_container_width=True)
            
    with st.expander("📚 Referência Científica"):
        st.markdown("""
        **Stanley C, Lennon D, Moran C, Vasireddy A, Rowan F.** Risk scoring models for patients with proximal femur fractures: Qualitative systematic review assessing 30-day mortality and ease of use. *Injury*. 2023;54:111017.  
        **DOI:** [10.1016/j.injury.2023.111017](https://doi.org/10.1016/j.injury.2023.111017)
        """)
    st.markdown("</div>", unsafe_allow_html=True)
