import streamlit as st
from utils import gerar_grafico_velocimetro, gerar_grafico_waterfall, obter_texto_explicativo
from database import salvar_registro

def calcular_risco(ang_dorsal, degrau_art, var_ulnar, rest_cortical, ang_volar):
    # Cálculo de Instabilidade em Rádio Distal (Khajonvittayakul et al., 2025)
    pontos = 0.0
    contribs = {}
    
    # Fatores Iniciais
    if ang_dorsal:
        pontos += 1.5
        contribs["Angulação Dorsal > 20°"] = 1.5
        
    if degrau_art > 0:
        pontos += degrau_art
        contribs[f"Degrau Articular ({degrau_art}mm)"] = float(degrau_art)
        
    if var_ulnar:
        pontos += 2.0
        contribs["Variância Ulnar > 3 mm"] = 2.0
        
    # Fatores de Qualidade da Redução
    if rest_cortical == "Sobreposição Dorsal":
        pontos += 1.0
        contribs["Cortical: Sobreposição Dorsal"] = 1.0
    elif rest_cortical == "Sobreposição Volar":
        pontos += 2.0
        contribs["Cortical: Sobreposição Volar"] = 2.0
        
    if ang_volar:
        pontos += 2.0
        contribs["Angulação Volar (Pós-Redução) ≤ 0°"] = 2.0
        
    # Conversão do score para Valor Preditivo Positivo (VPP) de instabilidade
    if pontos <= 2.0:
        prob = 27.2  # Baixo
    elif pontos <= 5.0:
        prob = 78.1  # Moderado
    else:
        prob = 95.5  # Alto
        
    return prob, contribs, pontos

def renderizar_ui():
    st.markdown("<div class='calc-info'><b>O que avalia:</b> Prevê a instabilidade em <b>fraturas da extremidade distal do rádio</b> após redução fechada. Combina parâmetros radiográficos iniciais e do alinhamento pós-redução para guiar a decisão entre a manutenção do gesso ou a intervenção cirúrgica imediata.</div>", unsafe_allow_html=True)
    st.markdown("<div class='input-card'><h4>✋ Risco de Instabilidade (Rádio Distal)</h4>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Fatores Iniciais (Pré-Redução)")
        dr_ang_dorsal = st.toggle("Angulação Dorsal > 20°?")
        dr_degrau = st.number_input("Degrau Articular (mm):", min_value=0, max_value=20, value=0, step=1, help="Adiciona 1 ponto por cada milímetro de degrau intra-articular.")
        dr_var_ulnar = st.toggle("Variância Ulnar > 3 mm?")
        
    with c2:
        st.markdown("##### Fatores de Qualidade da Redução")
        dr_cortical = st.selectbox("Restauração da Cortical Volar:", ["Redução Anatômica", "Sobreposição Dorsal", "Sobreposição Volar"])
        dr_ang_volar = st.toggle("Angulação Volar Pós-Redução ≤ 0°?")
        
    if st.button("Calcular Risco de Instabilidade", key="btn_distal_radius_instability"):
        res, contribs, pontos_totais = calcular_risco(dr_ang_dorsal, dr_degrau, dr_var_ulnar, dr_cortical, dr_ang_volar)
        st.session_state.distal_radius_instability_res = (res, contribs, pontos_totais)
        params_str = f"Score: {pontos_totais} | Degrau: {dr_degrau}mm | Cortical: {dr_cortical}"
        salvar_registro("Instabilidade Rádio Distal", res, "risco", params_str)
        
    if st.session_state.get('distal_radius_instability_res'):
        res, contribs, pontos_totais = st.session_state.distal_radius_instability_res
        col_g, col_x = st.columns([1, 1.5])
        with col_g: 
            st.plotly_chart(gerar_grafico_velocimetro(res, "risco"), use_container_width=True)
        with col_x: 
            st.markdown("##### 🧠 Estratificação Clínica e Conduta")
            if pontos_totais <= 2.0:
                st.success(f"🟢 **Probabilidade Baixa (Score {pontos_totais}):** Indicação primária para manutenção do **Tratamento Conservador**.")
            elif pontos_totais <= 5.0:
                st.warning(f"🟡 **Probabilidade Moderada (Score {pontos_totais}):** Indicação para avaliação estrita à 1ª semana. Caso a **Variância Ulnar seja > 3 mm em 1 semana**, alterar para tratamento cirúrgico.")
            else:
                st.error(f"🔴 **Probabilidade Alta (Score {pontos_totais}):** Risco crítico de perda de redução (VPP 95.5%). Forte indicação para **Tratamento Cirúrgico**.")
                
            st.plotly_chart(gerar_grafico_waterfall(contribs, titulo="Construção do Score de Instabilidade"), use_container_width=True)
            
    with st.expander("📚 Referência Científica"):
        st.markdown("""
        **Khajonvittayakul N, Supichyangur K, Apivatgaroon A, Tantiyavarong P.** A Prediction Model for Instability in Adult Distal Radius Fractures: Integrating Post-Reduction and Follow-Up Indicators. *Journal of Clinical Medicine*. 2025;14(23):8336.  
        **DOI:** [10.3390/jcm14238336](https://doi.org/10.3390/jcm14238336)
        """)
    st.markdown("</div>", unsafe_allow_html=True)
