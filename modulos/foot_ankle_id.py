import streamlit as st
from utils import gerar_grafico_velocimetro, gerar_grafico_waterfall, obter_texto_explicativo
from database import salvar_registro

def calcular_risco(tabagismo, diabetes, tempo_cirurgia):
    # Cálculo baseado no Risk Severity Score de Bonsignore-Opp et al. (2024)
    pontos = 0
    contribs = {}
    
    if tabagismo:
        pontos += 1
        contribs["Tabagismo Atual"] = 1
        
    if diabetes:
        pontos += 2
        contribs["Diabetes"] = 2
        
    if tempo_cirurgia > 60:
        pontos += 1
        contribs["Tempo de Cirurgia > 60 min"] = 1
        
    # Mapeamento do score para o risco percentual de I&D em 90 dias
    risco_map = {
        0: 0.6,
        1: 1.1,
        2: 2.1,
        3: 4.0,
        4: 7.5
    }
    
    prob = risco_map.get(pontos, 7.5)
    
    return prob, contribs

def renderizar_ui():
    st.markdown("<div class='calc-info'><b>O que avalia:</b> Este modelo estima o risco de necessidade de <b>Irrigação e Desbridamento (I&D) nos primeiros 90 dias</b> após uma cirurgia de pé e tornozelo, devido a infecção do local cirúrgico.</div>", unsafe_allow_html=True)
    st.markdown("<div class='input-card'><h4>🦶 Risco de Infecção (Pé e Tornozelo)</h4>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Dados do Paciente")
        fa_tabagismo = st.toggle("O paciente é fumante atual?")
        fa_diabetes = st.toggle("O paciente possui diagnóstico de Diabetes?")
        
    with c2:
        st.markdown("##### Dados Cirúrgicos")
        fa_tempo = st.number_input("Tempo estimado da cirurgia (minutos):", min_value=0, max_value=600, value=45, step=15)
        
    if st.button("Calcular Risco de I&D (90 dias)", key="btn_foot_ankle"):
        res, contribs = calcular_risco(fa_tabagismo, fa_diabetes, fa_tempo)
        st.session_state.foot_ankle_id_res = (res, contribs)
        params_str = f"Tabagismo: {'Sim' if fa_tabagismo else 'Não'} | Diabetes: {'Sim' if fa_diabetes else 'Não'} | Tempo: {fa_tempo} min"
        salvar_registro("Risco I&D (Pé/Tornozelo)", res, "complicacao", params_str)
        
    if st.session_state.get('foot_ankle_id_res'):
        res, contribs = st.session_state.foot_ankle_id_res
        col_g, col_x = st.columns([1, 1.5])
        with col_g: 
            st.plotly_chart(gerar_grafico_velocimetro(res, "complicacao"), use_container_width=True)
        with col_x: 
            st.markdown("##### 🧠 Explicabilidade do Algoritmo (XAI)")
            if sum(contribs.values()) == 0:
                st.success("🟢 **Risco Mínimo (0.6%):** O paciente não apresenta nenhum dos fatores de risco principais para reintervenção.")
            else:
                st.markdown(obter_texto_explicativo(contribs))
            st.plotly_chart(gerar_grafico_waterfall(contribs, titulo="Impacto dos Fatores (Score de 0 a 4)"), use_container_width=True)
            
    with st.expander("📚 Referência Científica"):
        st.markdown("""
        **Bonsignore-Opp L, Malka MS, Gorroochurn P, et al.** What Is the Risk of Irrigation and Debridement Following Foot and Ankle Surgery? Development of a Risk Severity Scoring System. *Clinical Orthopaedics and Related Research*. 2024;482(12):2163-2169.  
        **DOI:** [10.1097/CORR.0000000000003177](https://doi.org/10.1097/CORR.0000000000003177)
        """)
    st.markdown("</div>", unsafe_allow_html=True)
