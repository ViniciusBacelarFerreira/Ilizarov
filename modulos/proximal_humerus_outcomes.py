import streamlit as st
from utils import gerar_grafico_velocimetro, gerar_grafico_waterfall, obter_texto_explicativo
from database import salvar_registro

def calcular_adequacao(ases, vas, sane, eq5d, rom, cms, dash):
    # Cálculo de Adequação do Protocolo de Seguimento (Richard et al., ASES Taskforce 2020)
    pontos = 0.0
    contribs = {}
    
    # Recomendações Principais (Padrão-Ouro ASES)
    if ases:
        pontos += 25.0
        contribs["Escore ASES"] = 25.0
    
    if vas:
        pontos += 20.0
        contribs["Dor (VAS)"] = 20.0
        
    if sane:
        pontos += 15.0
        contribs["Avaliação SANE / SSV"] = 15.0
        
    if eq5d:
        pontos += 20.0
        contribs["Saúde Geral (EQ-5D / SF-6D)"] = 20.0
        
    if rom:
        pontos += 20.0
        contribs["Amplitude de Movimento (ROM)"] = 20.0

    # Ferramentas não recomendadas como primárias pela força-tarefa, mas amplamente usadas
    if cms and not ases:
        contribs["Aviso: Constant-Murley"] = 0.0
    if dash and not sane:
        contribs["Aviso: DASH (Longo)"] = 0.0

    adequacao = min(100.0, pontos)
    
    return adequacao, contribs

def renderizar_ui():
    st.markdown("<div class='calc-info'><b>O que avalia:</b> Audita a qualidade da recolha de dados pós-operatórios em <b>fraturas do úmero proximal</b>. Baseado nas diretrizes da força-tarefa da <i>American Shoulder and Elbow Surgeons (ASES)</i> para padronização de desfechos clínicos.</div>", unsafe_allow_html=True)
    st.markdown("<div class='input-card'><h4>💪 Qualidade do Seguimento Funcional (Úmero Proximal)</h4>", unsafe_allow_html=True)
    
    st.markdown("<p style='font-size: 0.9rem; color: gray;'>Selecione os instrumentos de avaliação funcional que foram aplicados a este paciente na consulta atual:</p>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Métricas Recomendadas")
        ph_ases = st.toggle("Escore ASES (American Shoulder and Elbow Surgeons)?")
        ph_vas = st.toggle("Escala Visual Analógica (VAS) para Dor?")
        ph_sane = st.toggle("Escore SANE (Single Assessment Numeric Evaluation) ou SSV?")
        ph_eq5d = st.toggle("Métrica de Qualidade de Vida Geral (EQ-5D ou SF-6D)?")
        ph_rom = st.toggle("Avaliação objetiva de ROM (Elevação, Rotação Externa e Interna)?")
        
    with c2:
        st.markdown("##### Outras Métricas (Opcionais/Históricas)")
        ph_cms = st.toggle("Escore Constant-Murley (CMS)?", help="Usado em 65% dos estudos, mas carece de validação específica e exige dinamômetro.")
        ph_dash = st.toggle("Escore DASH ou QuickDASH?", help="Válido, mas apresenta alta carga de preenchimento para o paciente.")
        
    if st.button("Auditar Protocolo de Desfechos", key="btn_proximal_humerus"):
        res, contribs = calcular_adequacao(ph_ases, ph_vas, ph_sane, ph_eq5d, ph_rom, ph_cms, ph_dash)
        st.session_state.proximal_humerus_outcomes_res = (res, contribs)
        params_str = f"ASES: {ph_ases} | VAS: {ph_vas} | SANE: {ph_sane} | EQ5D: {ph_eq5d} | ROM: {ph_rom}"
        salvar_registro("Auditoria Seguimento Úmero P.", res, "melhora", params_str) # Usamos "melhora" para exibir verde em valores altos
        
    if st.session_state.get('proximal_humerus_outcomes_res'):
        res, contribs = st.session_state.proximal_humerus_outcomes_res
        col_g, col_x = st.columns([1, 1.5])
        with col_g: 
            st.plotly_chart(gerar_grafico_velocimetro(res, "melhora"), use_container_width=True)
        with col_x: 
            st.markdown("##### 🧠 Avaliação do Protocolo (Diretriz ASES)")
            if res == 100.0:
                st.success("🟢 **Seguimento Padrão-Ouro (100%):** Os dados deste paciente estão perfeitamente alinhados com as recomendações internacionais, sendo ideais para pesquisa clínica e publicações de alto impacto.")
            elif res >= 60.0:
                st.warning(f"🟡 **Seguimento Aceitável ({res}%):** Protocolo razoável. Considere adicionar métricas de saúde geral (EQ-5D) ou o escore ASES para maior completude.")
            else:
                st.error(f"🔴 **Seguimento Inadequado ({res}%):** Alto risco de subnotificação funcional. Recomenda-se urgentemente a aplicação do escore ASES e medição de ROM.")
                
            if "Aviso: Constant-Murley" in contribs:
                st.info("💡 **Nota sobre CMS:** O escore Constant-Murley é histórico, mas a força-tarefa da ASES desaconselha o seu uso primário devido a dificuldades na padronização da força com dinamômetro na fratura do úmero proximal.")
                
            st.plotly_chart(gerar_grafico_waterfall(contribs, titulo="Contribuição para o Protocolo Ideal"), use_container_width=True)
            
    with st.expander("📚 Referência Científica"):
        st.markdown("""
        **Richard GJ, Denard PJ, Kaar SG, et al.** Outcome measures reported for the management of proximal humeral fractures: a systematic review. *Journal of Shoulder and Elbow Surgery*. 2020;29(10):2175-2184.  
        **DOI:** [10.1016/j.jse.2020.04.006](https://doi.org/10.1016/j.jse.2020.04.006)
        """)
    st.markdown("</div>", unsafe_allow_html=True)
