import streamlit as st
from utils import gerar_grafico_velocimetro, gerar_grafico_waterfall, obter_texto_explicativo
from database import salvar_registro

def calcular_risco(idade, imc, tamanho_lesao, tecnica):
    # Cálculo proxy baseado nas correlações negativas de Migliorini et al. (2023)
    pontos = 0.0
    contribs = {}
    
    if idade > 40:
        pontos += 2.0
        contribs["Idade Avançada (> 40 anos)"] = 2.0
        
    if imc >= 30.0:
        pontos += 3.0
        contribs["Obesidade (IMC ≥ 30)"] = 3.0
    elif imc >= 25.0:
        pontos += 1.0
        contribs["Sobrepeso (IMC ≥ 25)"] = 1.0
        
    if tamanho_lesao > 4.0:
        pontos += 3.0
        contribs["Defeito Extenso (> 4 cm²)"] = 3.0
    elif tamanho_lesao > 2.0:
        pontos += 1.5
        contribs["Defeito Moderado (> 2 cm²)"] = 1.5
        
    if tecnica == "Microfratura (MFx)" and tamanho_lesao > 2.0:
        pontos += 3.5
        contribs["Microfratura em Lesão > 2 cm²"] = 3.5
        
    # Conversão do score para probabilidade estimada de mau prognóstico/falha a médio prazo
    prob = min(99.9, (pontos / 11.5) * 85.0 + 5.0)
    
    return round(prob, 1), contribs

def renderizar_ui():
    st.markdown("<div class='calc-info'><b>O que avalia:</b> Estima o risco de <b>Mau Prognóstico ou Falha Clínica</b> no tratamento cirúrgico de lesões condrais (Joelho e Tornozelo). O modelo utiliza dados de uma extensa revisão sistemática para prever a deterioração dos resultados funcionais.</div>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class='calc-info' style='background-color: rgba(21, 101, 192, 0.05); border-left-color: #1565c0;'>
    💡 <b>Explicação dos Preditores (Migliorini et al., 2023):</b><br>
    • <b>Idade e IMC:</b> O envelhecimento reduz o potencial condrogênico das células-tronco, enquanto o sobrepeso sobrecarrega biomecanicamente o reparo articular recém-formado.<br>
    • <b>Tamanho do Defeito:</b> Lesões maiores exigem arcabouços biológicos mais complexos. O tamanho afeta negativamente o desfecho de quase todas as técnicas.<br>
    • <b>Escolha da Técnica:</b> A Microfratura (MFx) produz fibrocartilagem (colágeno tipo I), que se deteriora com o tempo e falha drasticamente em lesões > 2 cm². Técnicas como OAT, ACI ou AMIC são recomendadas para lesões maiores para garantir tecido hialino (colágeno tipo II).
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='input-card'><h4>🦵 Risco de Falha no Reparo de Cartilagem</h4>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Dados do Paciente")
        cond_idade = st.number_input("Idade do paciente (anos):", min_value=10, max_value=100, value=35)
        cond_peso = st.number_input("Peso (kg):", min_value=30.0, max_value=200.0, value=75.0)
        cond_altura = st.number_input("Altura (m):", min_value=1.0, max_value=2.5, value=1.75)
        imc_calc = cond_peso / (cond_altura ** 2)
        st.info(f"📐 IMC Calculado: {imc_calc:.1f} kg/m²")
        
    with c2:
        st.markdown("##### Dados da Lesão e Cirurgia")
        cond_local = st.selectbox("Articulação acometida:", ["Joelho", "Tornozelo (Tálus)"])
        cond_tamanho = st.number_input("Área total do defeito condral (cm²):", min_value=0.1, max_value=20.0, value=1.5, step=0.5)
        cond_tecnica = st.selectbox("Técnica Cirúrgica Planejada:", [
            "Microfratura (MFx)", 
            "Transplante Osteocondral Autólogo (OAT / Mosaicoplastia)", 
            "Implante Autólogo de Condrócitos (ACI)", 
            "Condrogênese Induzida por Matriz (AMIC)"
        ])
        
    if st.button("Calcular Risco de Falha", key="btn_chondral"):
        res, contribs = calcular_risco(cond_idade, imc_calc, cond_tamanho, cond_tecnica)
        st.session_state.chondral_defects_res = (res, contribs)
        params_str = f"Local: {cond_local} | Lesão: {cond_tamanho} cm² | Técnica: {cond_tecnica}"
        salvar_registro("Prognóstico Lesão Condral", res, "risco", params_str)
        
    if st.session_state.get('chondral_defects_res'):
        res, contribs = st.session_state.chondral_defects_res
        col_g, col_x = st.columns([1, 1.5])
        with col_g: 
            st.plotly_chart(gerar_grafico_velocimetro(res, "risco"), use_container_width=True)
        with col_x: 
            st.markdown("##### 🧠 Avaliação Prognóstica (XAI)")
            if sum(contribs.values()) <= 2.0:
                st.success("🟢 **Excelente Prognóstico:** Paciente jovem, com IMC adequado e lesão condizente com a técnica. A chance de sucesso clínico e restauração funcional é muito alta.")
            elif "Microfratura em Lesão > 2 cm²" in contribs:
                st.error("🔴 **Alerta de Má Indicação:** O uso de Microfratura em lesões extensas possui altíssima taxa de deterioração estrutural. Considere alterar a técnica para OAT, AMIC ou ACI.")
                st.plotly_chart(gerar_grafico_waterfall(contribs, titulo="Impacto Biomecânico e Cirúrgico"), use_container_width=True)
            else:
                st.warning("🟡 **Atenção aos Fatores de Risco:** O paciente apresenta desafios biológicos (ex: obesidade, idade ou lesão extensa) que podem comprometer a longevidade do reparo cartilaginoso. Orientar o paciente sobre controle de peso e expectativas de reabilitação.")
                st.plotly_chart(gerar_grafico_waterfall(contribs, titulo="Impacto Biomecânico e Cirúrgico"), use_container_width=True)
                
    with st.expander("📚 Referência Científica"):
        st.markdown("""
        **Migliorini F, Maffulli N, Eschweiler J, Götze C, Hildebrand F, Betsch M.** Prognostic factors for the management of chondral defects of the knee and ankle joint: a systematic review. *European Journal of Trauma and Emergency Surgery*. 2023;49:723-745.  
        **DOI:** [10.1007/s00068-022-02155-y](https://doi.org/10.1007/s00068-022-02155-y)
        """)
    st.markdown("</div>", unsafe_allow_html=True)
