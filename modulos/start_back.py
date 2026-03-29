import streamlit as st
from utils import gerar_grafico_velocimetro, gerar_grafico_waterfall
from database import salvar_registro

def calcular_risco(q1, q2, q3, q4, q5, q6, q7, q8, q9):
    pontos_fisicos = sum([1 for q in [q1, q2, q3, q4] if q])
    pontos_psico = sum([1 for q in [q5, q6, q7, q8] if q])
    
    if q9 in ["Muito", "Extremamente"]:
        pontos_psico += 1
        
    total = pontos_fisicos + pontos_psico
    
    if total <= 3: prob = 15.0 # Risco Baixo
    elif pontos_psico <= 3: prob = 50.0 # Risco Médio
    else: prob = 85.0 # Risco Alto
        
    contribs = {
        "Fatores Físicos (0-4)": pontos_fisicos,
        "Fatores Psicossociais (0-5)": pontos_psico
    }
    
    return prob, contribs

def renderizar_ui():
    st.markdown("<div class='calc-info'><b>O que avalia:</b> O <b>STarT Back Screening Tool</b> identifica preditores físicos e psicossociais para dor lombar persistente.</div>", unsafe_allow_html=True)
    st.markdown("<div class='input-card'><h4>🏃 STarT Back (Risco na Dor Lombar)</h4>", unsafe_allow_html=True)
    
    sb1, sb2 = st.columns(2)
    with sb1:
        st.markdown("##### Fatores Físicos (Últimas 2 semanas)")
        sb_q1 = st.toggle("1. A minha dor nas costas espalhou-se para a(s) perna(s).")
        sb_q2 = st.toggle("2. Tive dor no ombro ou no pescoço.")
        sb_q3 = st.toggle("3. Só caminhei curtas distâncias por causa da minha dor nas costas.")
        sb_q4 = st.toggle("4. Vesti-me mais lentamente que o normal por causa da dor.")
    with sb2:
        st.markdown("##### Fatores Psicossociais (Últimas 2 semanas)")
        sb_q5 = st.toggle("5. Não é seguro para uma pessoa com o meu problema ser fisicamente ativa.")
        sb_q6 = st.toggle("6. Pensamentos preocupantes têm passado pela minha cabeça muitas vezes.")
        sb_q7 = st.toggle("7. Sinto que a minha dor nas costas é terrível e que nunca vai melhorar.")
        sb_q8 = st.toggle("8. Em geral, não tenho aproveitado todas as coisas que costumava aproveitar.")
    
    sb_q9 = st.selectbox("9. No geral, quão incómoda foi a sua dor nas costas nas últimas 2 semanas?", ["Nada", "Ligeiramente", "Moderadamente", "Muito", "Extremamente"])
    
    if st.button("Calcular Risco de Cronicidade (STarT Back)", key="btn_sb"):
        res, contribs = calcular_risco(sb_q1, sb_q2, sb_q3, sb_q4, sb_q5, sb_q6, sb_q7, sb_q8, sb_q9)
        params = f"Físicos: {contribs['Fatores Físicos (0-4)']} pts | Psico: {contribs['Fatores Psicossociais (0-5)']} pts"
        st.session_state.start_back_res = (res, contribs)
        salvar_registro("STarT Back (Dor Lombar)", res, "risco", params)
    
    if st.session_state.start_back_res:
        res, contribs = st.session_state.start_back_res
        col_g, col_x = st.columns([1, 1.5])
        with col_g:
            st.plotly_chart(gerar_grafico_velocimetro(res, "risco"), use_container_width=True)
        with col_x:
            st.markdown("##### 🧠 Classificação de Reabilitação")
            pontos_totais = sum(contribs.values())
            pontos_psico = contribs['Fatores Psicossociais (0-5)']
            if pontos_totais <= 3:
                st.info("🟢 **Baixo Risco:** Indicação de tratamento em cuidados primários, tranquilização.")
            elif pontos_psico <= 3:
                st.warning("🟡 **Risco Médio:** Indicação de fisioterapia conservadora focada no retorno funcional.")
            else:
                st.error("🔴 **Alto Risco:** Indicação de fisioterapia associada a abordagem psicossocial/cognitivo-comportamental.")
            
            st.plotly_chart(gerar_grafico_waterfall(contribs, titulo="Composição do Score STarT Back"), use_container_width=True)

    with st.expander("📚 Referência Científica"):
        st.markdown("""
        **Naye F, Décary S, Houle C, et al.** Six Externally Validated Prognostic Models Have Potential Clinical Value to Predict Patient Health Outcomes in the Rehabilitation of Musculoskeletal Conditions: A Systematic Review. *PTJ: Physical Therapy & Rehabilitation Journal*. 2023;103:1-10.  
        **DOI:** [10.1093/ptj/pzad021](https://doi.org/10.1093/ptj/pzad021)
        """)
    st.markdown("</div>", unsafe_allow_html=True)
