import streamlit as st
from utils import gerar_grafico_velocimetro, gerar_grafico_waterfall, obter_texto_explicativo
from database import salvar_registro

def calcular_risco(idade, tamanho_ap, retracao, inf_infraspinatus, bmd_osteoporose, trabalho_pesado):
    pontos = 0
    contribs = {}
    
    if idade > 70:
        pontos += 2
        contribs["Idade > 70 anos"] = 2
        
    if tamanho_ap > 2.5:
        pontos += 2
        contribs["Tamanho AP > 2.5 cm"] = 2
        
    if retracao >= 3:
        pontos += 4
        contribs["Retração ≥ 3 cm"] = 4
    elif retracao >= 2:
        pontos += 2
        contribs["Retração 2-3 cm"] = 2
    elif retracao >= 1:
        pontos += 1
        contribs["Retração 1-2 cm"] = 1
        
    if inf_infraspinatus:
        pontos += 3
        contribs["Infiltração Gordurosa (Grau ≥ 2)"] = 3
        
    if bmd_osteoporose:
        pontos += 2
        contribs["Baixa DMO (T-score ≤ -2.5)"] = 2
        
    if trabalho_pesado:
        pontos += 2
        contribs["Trabalho Físico Pesado"] = 2

    # Mapeamento baseado no Valor Preditivo Positivo (PPV) para o limiar de pontuação (Tabela 4 - Kwon et al., 2018)
    ppv_map = {
        0: 0.0, 1: 26.0, 2: 34.1, 3: 36.1, 4: 45.2, 5: 55.2, 
        6: 61.7, 7: 73.8, 8: 75.2, 9: 76.2, 10: 86.2, 
        11: 89.4, 12: 90.0, 13: 88.9, 14: 95.0, 15: 99.9
    }
    
    prob = ppv_map.get(pontos, 99.9)
    
    return prob, contribs

def renderizar_ui():
    st.markdown("<div class='calc-info'><b>O que avalia:</b> O <b>Rotator Cuff Healing Index (RoHI)</b> estima a probabilidade de falha na cicatrização anatómica do manguito rotador após reparação cirúrgica.</div>", unsafe_allow_html=True)
    st.markdown("<div class='input-card'><h4>💪 Manguito Rotador (Risco de Falha RoHI)</h4>", unsafe_allow_html=True)
    
    rc1, rc2 = st.columns(2)
    with rc1:
        st.markdown("##### Dados Clínicos")
        rohi_idade = st.number_input("Idade do paciente (anos):", min_value=0, max_value=120, value=60)
        rohi_trabalho = st.toggle("Profissão exige trabalho físico pesado (ex: operário, carga)?")
        rohi_bmd = st.toggle("Osteoporose documentada (DMO T-score ≤ -2.5)?")
        
    with rc2:
        st.markdown("##### Dados Imagiológicos e Cirúrgicos")
        rohi_tamanho = st.number_input("Tamanho da rotura anteroposterior (cm):", min_value=0.0, max_value=10.0, value=2.0, step=0.5)
        rohi_retracao = st.selectbox("Grau de retração tendínea (cm):", ["< 1 cm", "1 a < 2 cm", "2 a < 3 cm", "≥ 3 cm"])
        rohi_fatty = st.toggle("Infiltração gordurosa do Infraespinhoso ≥ Grau 2 (Goutallier)?")
        
    if st.button("Calcular Probabilidade de Falha (RoHI)", key="btn_rohi"):
        # Conversão da string de retração para valor numérico
        ret_val = 0
        if rohi_retracao == "1 a < 2 cm": ret_val = 1
        elif rohi_retracao == "2 a < 3 cm": ret_val = 2
        elif rohi_retracao == "≥ 3 cm": ret_val = 3
        
        res, contribs = calcular_risco(rohi_idade, rohi_tamanho, ret_val, rohi_fatty, rohi_bmd, rohi_trabalho)
        st.session_state.rotator_cuff_res = (res, contribs)
        
        # Guardar registo com os parâmetros principais
        pontos_tot = sum(contribs.values())
        params_str = f"Score RoHI: {pontos_tot}/15 | Idade: {rohi_idade} | Tamanho AP: {rohi_tamanho}cm"
        salvar_registro("RoHI (Manguito Rotador)", res, "risco", params_str)
        
    if st.session_state.get('rotator_cuff_res'):
        res, contribs = st.session_state.rotator_cuff_res
        col_g, col_x = st.columns([1, 1.5])
        with col_g: 
            st.plotly_chart(gerar_grafico_velocimetro(res, "risco"), use_container_width=True)
        with col_x: 
            st.markdown("##### 🧠 Subgrupos de Risco Clínico")
            pontos_totais = sum(contribs.values())
            if pontos_totais <= 4:
                st.success(f"🟢 **Grupo de Baixo Risco (Score {pontos_totais}/15):** Apenas 6.0% de falha global neste grupo. Excelente prognóstico de cicatrização anatómica.")
            elif pontos_totais <= 9:
                st.warning(f"🟡 **Grupo de Risco Moderado/Alto (Score {pontos_totais}/15):** Aproximadamente 55.2% de taxa de falha. Considerar otimização biológica ou reforço mecânico.")
            else:
                st.error(f"🔴 **Grupo de Risco Muito Alto (Score {pontos_totais}/15):** Aproximadamente 86.2% de taxa de falha. Informar adequadamente o doente; alto risco de rotura recorrente.")
                
            st.plotly_chart(gerar_grafico_waterfall(contribs, titulo="Impacto das Variáveis (RoHI)"), use_container_width=True)
            
    with st.expander("📚 Referência Científica"):
        st.markdown("""
        **Kwon J, Kim SH, Lee YH, Kim TI, Oh JH.** The Rotator Cuff Healing Index: A New Scoring System to Predict Rotator Cuff Healing After Surgical Repair. *The American Journal of Sports Medicine*. 2019;47(1):173-180.  
        **DOI:** [10.1177/0363546518810763](https://doi.org/10.1177/0363546518810763)
        """)
    st.markdown("</div>", unsafe_allow_html=True)
