import streamlit as st
from utils import gerar_grafico_velocimetro, gerar_grafico_waterfall, obter_texto_explicativo
from database import salvar_registro

def calcular_risco(sexo_feminino, osteoporose, cimento, soltura):
    pontos = 0.0
    contribs = {}
    
    if sexo_feminino:
        pontos += 1.5
        contribs["Sexo Feminino"] = 1.5
        
    if osteoporose:
        pontos += 2.0
        contribs["Osteoporose"] = 2.0
        
    if cimento == "Não cimentada (Press-fit)":
        pontos += 2.0
        contribs["Prótese Não Cimentada"] = 2.0
        
    if soltura:
        pontos += 2.5
        contribs["Sinais de Descolamento/Soltura"] = 2.5
        
    prob = min(99.9, (pontos / 8.0) * 15.0)
    return round(prob, 1), contribs

def renderizar_ui():
    st.markdown("<div class='calc-info'><b>O que avalia:</b> Estima o risco de <b>Fratura Periprotésica em 12 meses</b> após artroplastia de quadril em pacientes muito idosos (≥ 80 anos). O modelo permite estratificar o risco para otimizar o tratamento médico e cirúrgico.</div>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class='calc-info' style='background-color: rgba(21, 101, 192, 0.05); border-left-color: #1565c0;'>
    💡 <b>Explicação dos Preditores (Chen et al., 2024):</b><br>
    • <b>Sexo Feminino:</b> Pacientes do sexo feminino apresentam uma diminuição mais acentuada da massa óssea após a menopausa, tornando o osso mais suscetível a fraturas ao redor do implante.<br>
    • <b>Osteoporose:</b> A perda da densidade e da microarquitetura trabecular reduz a resistência mecânica do fêmur proximal.<br>
    • <b>Prótese Não Cimentada:</b> A inserção sob pressão ("press-fit") gera uma tensão de expansão transversal ("hoop stress") num osso cortical já enfraquecido, aumentando drasticamente o risco de fissuras iatrogênicas.<br>
    • <b>Descolamento/Soltura:</b> A micromovimentação da haste causa reabsorção óssea (osteólise) e instabilidade biomecânica, sendo o preditor de maior impacto.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='input-card'><h4>🦵 Risco de Fratura Periprotésica (≥ 80 anos)</h4>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Dados do Paciente")
        ppf_sexo = st.selectbox("Sexo biológico:", ["Feminino", "Masculino"])
        ppf_osteo = st.toggle("Possui diagnóstico de Osteoporose documentada?")
        
    with c2:
        st.markdown("##### Dados da Artroplastia")
        ppf_cimento = st.selectbox("Tipo de fixação da haste femoral:", ["Cimentada", "Não cimentada (Press-fit)"])
        ppf_soltura = st.toggle("Sinais radiográficos de descolamento ou soltura da prótese?")
        
    if st.button("Calcular Risco de Fratura Periprotésica", key="btn_ppf"):
        sexo_fem = True if ppf_sexo == "Feminino" else False
        res, contribs = calcular_risco(sexo_fem, ppf_osteo, ppf_cimento, ppf_soltura)
        st.session_state.periprosthetic_fracture_res = (res, contribs)
        params_str = f"Sexo: {ppf_sexo} | Osteoporose: {'Sim' if ppf_osteo else 'Não'} | Fixação: {ppf_cimento} | Soltura: {'Sim' if ppf_soltura else 'Não'}"
        salvar_registro("Fratura Periprotésica (Quadril)", res, "complicacao", params_str)
        
    if st.session_state.get('periprosthetic_fracture_res'):
        res, contribs = st.session_state.periprosthetic_fracture_res
        col_g, col_x = st.columns([1, 1.5])
        with col_g: 
            st.plotly_chart(gerar_grafico_velocimetro(res, "complicacao"), use_container_width=True)
        with col_x: 
            st.markdown("##### 🧠 Explicabilidade e Conduta (XAI)")
            if sum(contribs.values()) == 0:
                st.success("🟢 **Risco Mínimo:** Paciente otimizado. Manter acompanhamento clínico de rotina.")
            else:
                st.warning("⚠️ **Risco Elevado Identificado:** Considerar intervenção estratificada: terapia anti-osteoporótica precoce, prevenção de quedas e monitorização radiográfica intensiva da estabilidade da prótese.")
                st.plotly_chart(gerar_grafico_waterfall(contribs, titulo="Impacto dos Fatores de Risco"), use_container_width=True)
                
    with st.expander("📚 Referência Científica"):
        st.markdown("""
        **Chen X, Yuan Z.** Risk factors and risk-stratified prevention of periprosthetic fractures after hip arthroplasty in patients aged ≥80 years: A retrospective cohort study with prospective validation. *Medicine*. 2024;103:29(e39050).  
        **DOI:** [10.1097/MD.0000000000039050](https://doi.org/10.1097/MD.0000000000039050)
        """)
    st.markdown("</div>", unsafe_allow_html=True)
