import streamlit as st
from utils import gerar_grafico_velocimetro, gerar_grafico_waterfall, obter_texto_explicativo
from database import salvar_registro

def calcular_risco(idade, sexo, osteoporose, indicacao, abordagem, fixacao, colar):
    # Cálculo proxy baseado nos Hazard Ratios (HR) do modelo de Wyles et al. (2023) - Mayo Clinic
    pontos = 0.0
    contribs = {}
    
    # --- FATORES NÃO MODIFICÁVEIS ---
    # Idade (proxy: HR aumenta 1.2 a cada 10 anos a partir dos 50)
    if idade > 50:
        c_idade = ((idade - 50) / 10.0) * 1.2
        pontos += c_idade
        contribs["Idade Avançada"] = round(c_idade, 1)
        
    if sexo == "Feminino":
        pontos += 1.6
        contribs["Sexo Feminino"] = 1.6
        
    if osteoporose:
        pontos += 1.7
        contribs["Osteoporose"] = 1.7
        
    if indicacao == "Fratura / Pós-Traumática":
        pontos += 2.2
        contribs["Indicação: Fratura"] = 2.2
    elif indicacao == "Artrite Inflamatória":
        pontos += 1.8
        contribs["Indicação: Artrite Inflam."] = 1.8
    elif indicacao == "Osteonecrose (AVN)":
        pontos += 1.7
        contribs["Indicação: Osteonecrose"] = 1.7
        
    # --- FATORES MODIFICÁVEIS (CIRÚRGICOS) ---
    if abordagem == "Lateral":
        pontos += 2.9
        contribs["Abordagem Lateral"] = 2.9
    elif abordagem == "Posterior":
        pontos += 1.9
        contribs["Abordagem Posterior"] = 1.9
        
    if fixacao == "Não Cimentada":
        pontos += 2.5
        contribs["Fixação Não Cimentada"] = 2.5
        
    if colar == "Sem Colar (Collarless)":
        pontos += 1.3
        contribs["Haste Sem Colar"] = 1.3

    # Interpolação para Risco Absoluto aos 90 dias
    # Baseado no "Best Host" (0.4%) e "Worst Host" (18.0%) da Tabela 4 do estudo
    risco_base = 0.4
    risco_maximo = 18.0
    max_pontos_possiveis = 17.0 
    
    prob = risco_base + (pontos / max_pontos_possiveis) * (risco_maximo - risco_base)
    prob = min(prob, 99.9)
    
    return round(prob, 1), contribs

def renderizar_ui():
    st.markdown("<div class='calc-info'><b>O que avalia:</b> Calculadora <i>Patient-Specific</i> da Mayo Clinic para o risco de <b>Fratura Periprotésica em 90 dias</b> após Artroplastia Total do Quadril (ATQ). Demonstra como as escolhas cirúrgicas podem mitigar os riscos inerentes do paciente.</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='input-card'><h4>🦵 Risco de Fratura Periprotésica (Calculadora Mayo Clinic)</h4>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### 👤 Fatores Não Modificáveis")
        tha_idade = st.number_input("Idade do paciente (anos):", min_value=18, max_value=120, value=65)
        tha_sexo = st.selectbox("Sexo biológico:", ["Masculino", "Feminino"], key="tha_sexo")
        tha_osteo = st.toggle("Osteoporose documentada ou uso de medicação óssea?", key="tha_osteo")
        tha_ind = st.selectbox("Indicação Primária para a ATQ:", [
            "Osteoartrite Primária", 
            "Osteonecrose (AVN)", 
            "Artrite Inflamatória", 
            "Fratura / Pós-Traumática"
        ])
        
    with c2:
        st.markdown("##### 🛠️ Fatores Modificáveis (Cirúrgicos)")
        tha_abord = st.selectbox("Abordagem Cirúrgica:", [
            "Anterior Direta (DAA)", 
            "Posterior", 
            "Lateral"
        ])
        tha_fix = st.selectbox("Fixação Femoral:", [
            "Cimentada", 
            "Não Cimentada"
        ])
        tha_colar = st.selectbox("Tipo de Implante Femoral:", [
            "Com Colar (Collared)", 
            "Sem Colar (Collarless)"
        ])
        
    if st.button("Calcular Risco e Mitigação", key="btn_tha_ppf"):
        res, contribs = calcular_risco(tha_idade, tha_sexo, tha_osteo, tha_ind, tha_abord, tha_fix, tha_colar)
        st.session_state.tha_periprosthetic_fracture_res = (res, contribs)
        params_str = f"Indicação: {tha_ind} | Abordagem: {tha_abord} | Fixação: {tha_fix} | Implante: {tha_colar}"
        salvar_registro("Fratura Periprotésica (ATQ - Mayo)", res, "complicacao", params_str)
        
    if st.session_state.get('tha_periprosthetic_fracture_res'):
        res, contribs = st.session_state.tha_periprosthetic_fracture_res
        col_g, col_x = st.columns([1, 1.5])
        with col_g: 
            # Como a incidência geral é baixa (0.4% a 18%), vamos ajustar o medidor visualmente
            st.plotly_chart(gerar_grafico_velocimetro(res, "complicacao"), use_container_width=True)
            st.markdown(f"<p style='text-align: center; font-size: 1.2rem; font-weight: bold; color: {'red' if res > 5.0 else 'orange' if res > 2.0 else 'green'};'>Risco Absoluto (90 dias): {res}%</p>", unsafe_allow_html=True)
            
        with col_x: 
            st.markdown("##### 🧠 Análise de Modificação de Risco (XAI)")
            if sum(contribs.values()) == 0:
                st.success("🟢 **Risco Mínimo:** Paciente ideal com escolhas cirúrgicas de menor risco biomecânico.")
            else:
                fatores_modificaveis_presentes = any(k in contribs for k in ["Abordagem Lateral", "Abordagem Posterior", "Fixação Não Cimentada", "Haste Sem Colar"])
                
                if fatores_modificaveis_presentes:
                    st.warning("⚠️ **Estratégia de Mitigação:** Note no gráfico abaixo o peso das suas escolhas cirúrgicas. A utilização de haste cimentada, implante com colar ou abordagem anterior direta pode reduzir drasticamente a probabilidade de fratura neste paciente.")
                else:
                    st.info("💡 **Risco Inerente Elevado:** O paciente possui risco ditado pela sua biologia. As suas escolhas cirúrgicas (Cimentada, Com Colar, DAA) já estão a proporcionar a máxima mitigação possível.")
                    
                st.plotly_chart(gerar_grafico_waterfall(contribs, titulo="Impacto Fatores Inerentes vs Modificáveis"), use_container_width=True)
                
    with st.expander("📚 Referência Científica"):
        st.markdown("""
        **Wyles CC, Maradit-Kremers H, Fruth KM, et al.** Frank Stinchfield Award: Creation of a Patient-Specific Total Hip Arthroplasty Periprosthetic Fracture Risk Calculator. *The Journal of Arthroplasty*. 2023;38(7):S2-S10.  
        **DOI:** [10.1016/j.arth.2023.03.031](https://doi.org/10.1016/j.arth.2023.03.031)
        """)
    st.markdown("</div>", unsafe_allow_html=True)
