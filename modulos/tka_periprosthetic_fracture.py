import streamlit as st
from utils import gerar_grafico_velocimetro, gerar_grafico_waterfall, obter_texto_explicativo
from database import salvar_registro

def calcular_risco(sexo_feminino, notching, osteoporose, parkinson, cardiovascular, lado_esquerdo):
    # Cálculo proxy baseado nos Odds Ratios do estudo de Li et al. (2025)
    pontos = 0.0
    contribs = {}
    
    # Doença de Parkinson (OR = 7.48)
    if parkinson:
        pontos += 7.5
        contribs["Doença de Parkinson"] = 7.5
        
    # Anterior Femoral Notching (OR = 3.12)
    if notching:
        pontos += 3.1
        contribs["Notching Femoral Anterior"] = 3.1
        
    # Doença Cardiovascular (OR = 2.23)
    if cardiovascular:
        pontos += 2.2
        contribs["Doença Cardiovascular"] = 2.2
        
    # Sexo Feminino (OR = 1.81)
    if sexo_feminino:
        pontos += 1.8
        contribs["Sexo Feminino"] = 1.8
        
    # Osteoporose (OR = 1.68)
    if osteoporose:
        pontos += 1.7
        contribs["Osteoporose"] = 1.7
        
    # Lateralidade Esquerda (OR = 1.68)
    if lado_esquerdo:
        pontos += 1.7
        contribs["Lateralidade (Joelho Esquerdo)"] = 1.7
        
    # Conversão do score para probabilidade estimada de risco (ajustado para representar agravamento da incidência base de 3.5%)
    prob = min(99.9, (pontos / 18.0) * 25.0)
    
    return round(prob, 1), contribs

def renderizar_ui():
    st.markdown("<div class='calc-info'><b>O que avalia:</b> Estima o risco de <b>Fratura Periprotésica após Artroplastia Total do Joelho (ATJ)</b> com base em uma meta-análise de 3.7 milhões de casos. Ajuda a antecipar o risco estrutural e sistêmico do paciente.</div>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class='calc-info' style='background-color: rgba(21, 101, 192, 0.05); border-left-color: #1565c0;'>
    💡 <b>Explicação dos Preditores (Li et al., 2025):</b><br>
    • <b>Notching Femoral Anterior:</b> Ressecção óssea excessiva na cortical anterior do fêmur que cria um ponto de concentração de estresse mecânico, facilitando fraturas supracondilianas.<br>
    • <b>Doença de Parkinson:</b> Pacientes possuem menor densidade óssea devido a desnutrição e sofrem de disfunção motora severa, aumentando drasticamente o risco de quedas e trauma sobre a prótese.<br>
    • <b>Doença Cardiovascular:</b> O uso de medicações cardiológicas e a diminuição de proteínas ósseas (esclerostina) afetam o metabolismo do osso, tornando-o mais frágil.<br>
    • <b>Osteoporose & Sexo Feminino:</b> A diminuição do estrogênio pós-menopausa causa reabsorção óssea acelerada, reduzindo o suporte ósseo do implante.<br>
    • <b>Lateralidade (Esquerda):</b> Encontrada associação estatística independente para o joelho esquerdo na literatura global, possivelmente ligada a assimetrias de marcha.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='input-card'><h4>🦵 Risco de Fratura Periprotésica (Artroplastia de Joelho)</h4>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Variáveis Sistêmicas")
        tka_sexo = st.selectbox("Sexo biológico:", ["Masculino", "Feminino"])
        tka_parkinson = st.toggle("Possui Doença de Parkinson?")
        tka_cardio = st.toggle("Possui Doença Cardiovascular preexistente?")
        tka_osteo = st.toggle("Possui diagnóstico de Osteoporose?")
        
    with c2:
        st.markdown("##### Fatores Cirúrgicos e Anatômicos")
        tka_lado = st.selectbox("Lado operado:", ["Direito", "Esquerdo"])
        tka_notching = st.toggle("Identificado 'Notching' (Entalhe) na cortical femoral anterior?")
        
    if st.button("Calcular Risco de Fratura (Joelho)", key="btn_tka_ppf"):
        sexo_fem = True if tka_sexo == "Feminino" else False
        lado_esq = True if tka_lado == "Esquerdo" else False
        
        res, contribs = calcular_risco(sexo_fem, tka_notching, tka_osteo, tka_parkinson, tka_cardio, lado_esq)
        st.session_state.tka_periprosthetic_fracture_res = (res, contribs)
        params_str = f"Notching: {'Sim' if tka_notching else 'Não'} | Parkinson: {'Sim' if tka_parkinson else 'Não'} | Sexo: {tka_sexo}"
        salvar_registro("Fratura Periprotésica (Joelho)", res, "complicacao", params_str)
        
    if st.session_state.get('tka_periprosthetic_fracture_res'):
        res, contribs = st.session_state.tka_periprosthetic_fracture_res
        col_g, col_x = st.columns([1, 1.5])
        with col_g: 
            st.plotly_chart(gerar_grafico_velocimetro(res, "complicacao"), use_container_width=True)
        with col_x: 
            st.markdown("##### 🧠 Explicabilidade e Conduta (XAI)")
            if sum(contribs.values()) == 0:
                st.success("🟢 **Risco Base Padrão:** O paciente não possui os agravantes listados. O risco de fratura periprotésica reflete a base populacional (< 3%).")
            else:
                st.warning("⚠️ **Risco Elevado Identificado:** O paciente possui fatores que agravam substancialmente o risco estrutural. Considere tratamento intensivo para osteoporose, proteção contra quedas e, se houver 'notching', monitoramento radiográfico rigoroso.")
                st.plotly_chart(gerar_grafico_waterfall(contribs, titulo="Peso dos Fatores de Risco (Baseado em OR)"), use_container_width=True)
                
    with st.expander("📚 Referência Científica"):
        st.markdown("""
        **Li H, Liu C, Jin G, et al.** Risk Factors for Periprosthetic Fractures After Total Knee Arthroplasty: A Systematic Review and Meta-Analysis. *The Journal of Arthroplasty*. 2025;40:3046-3055.  
        **DOI:** [10.1016/j.arth.2025.05.044](https://doi.org/10.1016/j.arth.2025.05.044)
        """)
    st.markdown("</div>", unsafe_allow_html=True)
