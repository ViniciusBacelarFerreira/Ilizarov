import streamlit as st
from utils import gerar_grafico_velocimetro, gerar_grafico_waterfall
from database import salvar_registro

def calcular_risco(idade, sexo, fratura_previa, frax_mof, fratura_em_tratamento):
    pontos = frax_mof
    contribs = {"Risco FRAX (MOF) base": frax_mof}
    
    if fratura_previa:
        acrescimo = max(0, 50 - pontos) 
        pontos += acrescimo
        contribs["Fratura Prévia (Indicação Direta)"] = acrescimo
        
    if fratura_em_tratamento:
        acrescimo_falha = max(0, 80 - pontos)
        pontos += acrescimo_falha
        contribs["Falha Terapêutica"] = acrescimo_falha

    prob = min(pontos, 99.9)
    recomenda = []
    
    if (sexo == "Feminino" and idade >= 65) or (sexo == "Masculino" and idade >= 70):
        recomenda.append("✔️ Rastreamento Densitométrico (DXA) indicado pela idade.")
    if fratura_previa:
        recomenda.append("⚠️ Indicação direta para intervenção farmacológica devido a fratura prévia.")
    if frax_mof >= 35:
        recomenda.append("💉 Limiar de custo-efetividade atingido para Denosumabe (MOF ≥ 35%).")
    elif frax_mof >= 20:
        recomenda.append("💉 Limiar de custo-efetividade atingido para Bisfosfonato Intravenoso (MOF ≥ 20%).")
    elif frax_mof >= 9:
        recomenda.append("💊 Limiar de custo-efetividade atingido para Bisfosfonato Oral (MOF ≥ 9%).")
    if fratura_em_tratamento:
        recomenda.append("🚨 FRATURA DURANTE TRATAMENTO: Avaliar adesão (>70-80%). Descartar causas secundárias. Considerar via parenteral ou anabólicos.")

    return prob, contribs, recomenda

def renderizar_ui():
    st.markdown("<div class='calc-info'><b>O que avalia:</b> Diretrizes de avaliação de risco de osteoporose e limiares terapêuticos.</div>", unsafe_allow_html=True)
    st.markdown("<div class='input-card'><h4>🦴 Estratificação FRAX & Decisão</h4>", unsafe_allow_html=True)
    
    o1, o2 = st.columns(2)
    with o1:
        osteo_idade = st.number_input("Idade do paciente:", min_value=0, max_value=120, value=70)
        osteo_sexo = st.selectbox("Sexo do paciente:", ["Feminino", "Masculino"], key="osteo_s")
        osteo_frax = st.number_input("Risco FRAX a 10 anos para Fratura Maior (MOF %):", min_value=0.0, max_value=100.0, value=5.0)
    with o2:
        osteo_prev = st.toggle("Possui histórico de fratura por fragilidade?")
        osteo_falha = st.toggle("Sofreu nova fratura enquanto recebia tratamento?")
        
    if st.button("Avaliar Decisão Clínica", key="btn_osteo"):
        res, contribs, recomenda = calcular_risco(osteo_idade, osteo_sexo, osteo_prev, osteo_frax, osteo_falha)
        st.session_state.osteo_res = (res, contribs, recomenda)
        salvar_registro("Risco Osteoporose", res, "risco", f"FRAX MOF: {osteo_frax}%")
        
    if st.session_state.get('osteo_res'):
        res, contribs, recomenda = st.session_state.osteo_res
        col_g, col_x = st.columns([1, 1.5])
        with col_g: st.plotly_chart(gerar_grafico_velocimetro(res, "risco"), use_container_width=True)
        with col_x:
            st.markdown("##### 🩺 Recomendações Clínicas")
            for rec in recomenda: st.info(rec)
            st.plotly_chart(gerar_grafico_waterfall(contribs, titulo="Composição do Risco Modificado"), use_container_width=True)
            
    with st.expander("📚 Referência Científica"):
        st.markdown("""
        **Ye C, Ebeling P, Kline G.** Osteoporosis. *The Lancet*. 2025;406:2003-16.  
        **DOI:** [10.1016/S0140-6736(25)01385-6](https://doi.org/10.1016/S0140-6736(25)01385-6)
        """)
    st.markdown("</div>", unsafe_allow_html=True)
