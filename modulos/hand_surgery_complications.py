import streamlit as st
from utils import gerar_grafico_velocimetro, gerar_grafico_waterfall, obter_texto_explicativo
from database import salvar_registro

def calcular_risco(hipoalbuminemia, icc, anemia, creatinina, sexo_masc, tabagismo, hiponatremia):
    # Cálculo baseado no Risk Stratification Scoring System de Hustedt et al. (2018) 
    pontos = 0
    contribs = {}
    
    if hipoalbuminemia:
        pontos += 5
        contribs["Hipoalbuminemia (< 3.5 g/dL)"] = 5
        
    if icc:
        pontos += 2
        contribs["Insuf. Cardíaca Congestiva"] = 2
        
    if anemia:
        pontos += 2
        contribs["Anemia"] = 2
        
    if creatinina:
        pontos += 2
        contribs["Creatinina Elevada (> 1.3 mg/dL)"] = 2
        
    if sexo_masc:
        pontos += 1
        contribs["Sexo Masculino"] = 1
        
    if tabagismo:
        pontos += 1
        contribs["Tabagismo Atual"] = 1
        
    if hiponatremia:
        pontos += 1
        contribs["Hiponatremia (< 135 mEq/L)"] = 1

    # Mapeamento do score para o risco percentual de complicações em 30 dias 
    if pontos <= 3:
        prob = 2.4
        classificacao = "Risco Baixo"
    elif pontos <= 7:
        prob = 10.4
        classificacao = "Risco Médio"
    else:
        prob = 28.9
        classificacao = "Risco Alto"
        
    return prob, contribs, classificacao, pontos

def renderizar_ui():
    st.markdown("<div class='calc-info'><b>O que avalia:</b> Estima o risco de <b>Complicações Cirúrgicas Gerais em 30 dias</b> para pacientes submetidos a cirurgias da Mão e Punho. Utiliza fatores demográficos e marcadores laboratoriais essenciais.</div>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class='calc-info' style='background-color: rgba(21, 101, 192, 0.05); border-left-color: #1565c0;'>
    💡 <b>Explicação dos Preditores (Hustedt et al., 2018):</b><br>
    • <b>Hipoalbuminemia (+5 pontos):</b> Forte indicador de desnutrição e reserva fisiológica comprometida, sendo o fator isolado de maior impacto para infecções e falha de cicatrização.<br>
    • <b>ICC, Anemia e Creatinina Alta (+2 pontos cada):</b> Representam o comprometimento do transporte de oxigênio aos tecidos e disfunção sistêmica de órgãos vitais (coração e rins).<br>
    • <b>Tabagismo, Hiponatremia e Sexo Masculino (+1 ponto cada):</b> Fatores metabólicos e comportamentais aditivos que elevam a incidência de complicações na janela de 30 dias pós-operatórios.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='input-card'><h4>✋ Risco de Complicações (Cirurgia da Mão)</h4>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Fatores Clínicos e Demográficos")
        hand_sexo = st.selectbox("Sexo biológico:", ["Feminino", "Masculino"], key="hand_sexo")
        hand_tabagismo = st.toggle("Tabagismo atual?", key="hand_tab")
        hand_icc = st.toggle("Possui Insuficiência Cardíaca Congestiva (ICC)?", key="hand_icc")
        
    with c2:
        st.markdown("##### Marcadores Laboratoriais (Pré-Operatórios)")
        hand_albumina = st.toggle("Hipoalbuminemia (Albumina < 3.5 g/dL)?", key="hand_alb")
        hand_anemia = st.toggle("Anemia (Hematócrito < 42% no homem ou < 38% na mulher)?", key="hand_ane")
        hand_creatinina = st.toggle("Creatinina Elevada (> 1.3 mg/dL)?", key="hand_crea")
        hand_sodio = st.toggle("Hiponatremia (Sódio < 135 mEq/L)?", key="hand_sodio")
        
    if st.button("Calcular Risco de Complicação Geral (30 dias)", key="btn_hand_comp"):
        sexo_masc = True if hand_sexo == "Masculino" else False
        res, contribs, classif, pts = calcular_risco(hand_albumina, hand_icc, hand_anemia, hand_creatinina, sexo_masc, hand_tabagismo, hand_sodio)
        
        st.session_state.hand_surgery_complications_res = (res, contribs, classif, pts)
        params_str = f"Score: {pts} | Albumin<3.5: {hand_albumina} | Anemia: {hand_anemia} | ICC: {hand_icc}"
        salvar_registro("Complicações em Cirurgia da Mão", res, "complicacao", params_str)
        
    if st.session_state.get('hand_surgery_complications_res'):
        res, contribs, classif, pts = st.session_state.hand_surgery_complications_res
        col_g, col_x = st.columns([1, 1.5])
        with col_g: 
            st.plotly_chart(gerar_grafico_velocimetro(res, "complicacao"), use_container_width=True)
            cor_txt = "green" if pts <= 3 else "orange" if pts <= 7 else "red"
            st.markdown(f"<p style='text-align: center; font-size: 1.2rem; font-weight: bold; color: {cor_txt};'>{classif} ({pts} pontos)</p>", unsafe_allow_html=True)
        with col_x: 
            st.markdown("##### 🧠 Explicabilidade e Conduta (XAI)")
            if pts <= 3:
                st.success("🟢 **Baixo Risco (2.4%):** O paciente está otimizado para o procedimento. As chances de complicação cirúrgica sistêmica são pequenas.")
            elif pts <= 7:
                st.warning("🟡 **Risco Médio (10.4%):** Há um risco 4.3 vezes maior de complicações em comparação a pacientes otimizados. Considere correção de deficiências laboratoriais (ex: anemia, desidratação) antes de cirurgias eletivas.")
            else:
                st.error("🔴 **Risco Alto (28.9%):** Risco quase 12 vezes maior. Aconselha-se forte otimização nutricional (se hipoalbuminemia), controle cardiovascular e renal antes de autorizar o procedimento eletivo.")
                
            st.plotly_chart(gerar_grafico_waterfall(contribs, titulo="Impacto dos Marcadores no Score (0-13)"), use_container_width=True)
            
    with st.expander("📚 Referência Científica"):
        st.markdown("""
        **Hustedt JW, Chung A, Bohl DD.** Development of a Risk Stratification Scoring System to Predict General Surgical Complications in Hand Surgery Patients. *The Journal of Hand Surgery*. 2018;43(7):641-648.  
        **DOI:** [10.1016/j.jhsa.2018.05.001](https://doi.org/10.1016/j.jhsa.2018.05.001)
        """)
    st.markdown("</div>", unsafe_allow_html=True)
