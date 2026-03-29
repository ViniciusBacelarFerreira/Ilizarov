import streamlit as st
from utils import gerar_grafico_velocimetro, gerar_grafico_waterfall, obter_texto_explicativo
from database import salvar_registro

def calcular_risco_bonsignore(tabagismo, diabetes, tempo_cirurgia):
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
        
    risco_map = {0: 0.6, 1: 1.1, 2: 2.1, 3: 4.0, 4: 7.5}
    prob = risco_map.get(pontos, 7.5)
    return prob, contribs

def calcular_risco_deng(idade, diabetes, fratura_exposta, albumina_baixa, tempo_cirurgia):
    # Nomograma proxy para infecção incisional em fratura de tornozelo (Deng et al., 2023)
    pontos = 0
    contribs = {}

    c_idade = 35 if idade >= 60 else 0
    if c_idade: contribs["Idade ≥ 60 anos"] = c_idade; pontos += c_idade

    c_diab = 25 if diabetes else 0
    if c_diab: contribs["Diabetes Mellitus"] = c_diab; pontos += c_diab

    c_albumina = 55 if albumina_baixa else 0
    if c_albumina: contribs["Albumina < 35 g/L"] = c_albumina; pontos += c_albumina

    c_exposta = 100 if fratura_exposta else 0
    if c_exposta: contribs["Fratura Exposta"] = c_exposta; pontos += c_exposta

    c_tempo = 22 if tempo_cirurgia >= 120 else 0
    if c_tempo: contribs["Tempo Cirúrgico ≥ 2h"] = c_tempo; pontos += c_tempo

    # Interpolação baseada no eixo de probabilidade do Nomograma
    if pontos <= 0: prob = 2.0
    elif pontos <= 60: prob = 2.0 + ((pontos - 0) / 60) * 28.0
    elif pontos <= 85: prob = 30.0 + ((pontos - 60) / 25) * 10.0
    elif pontos <= 110: prob = 40.0 + ((pontos - 85) / 25) * 10.0
    elif pontos <= 130: prob = 50.0 + ((pontos - 110) / 20) * 10.0
    elif pontos <= 150: prob = 60.0 + ((pontos - 130) / 20) * 10.0
    elif pontos <= 175: prob = 70.0 + ((pontos - 150) / 25) * 10.0
    elif pontos <= 210: prob = 80.0 + ((pontos - 175) / 35) * 10.0
    elif pontos <= 240: prob = 90.0 + ((pontos - 210) / 30) * 5.0
    else: prob = 98.0

    return min(prob, 99.9), contribs

def renderizar_ui():
    st.markdown("<div class='calc-info'><b>Módulos de Risco Infeccioso:</b> Selecione abaixo o modelo preditivo adequado para o cenário do seu paciente.</div>", unsafe_allow_html=True)
    
    # Menu de seleção por pílulas (radio horizontal estilizado pelo CSS do app.py)
    modelo_infeccao = st.radio(
        "Modelos Disponíveis:",
        ["🦴 Infecção Incisional em Fratura de Tornozelo (Deng)", "🦶 Risco Geral de I&D em Cirurgia Eletiva/Geral (Bonsignore-Opp)"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    st.markdown("<br>", unsafe_allow_html=True)

    if "Deng" in modelo_infeccao:
        st.markdown("<div class='input-card'><h4>🦴 Risco de Infecção Incisional (Fratura de Tornozelo)</h4>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Dados Clínicos")
            deng_idade = st.number_input("Idade do paciente (anos):", min_value=0, max_value=120, value=65, key="deng_idade")
            deng_diabetes = st.toggle("O paciente possui Diabetes?", key="deng_diab")
            deng_albumina = st.toggle("Nível de Albumina sérica pré-operatória < 35 g/L?", key="deng_alb")
        with c2:
            st.markdown("##### Dados do Trauma e Cirurgia")
            deng_exposta = st.toggle("A fratura é exposta?", key="deng_exp")
            deng_tempo = st.number_input("Tempo estimado de cirurgia (minutos):", min_value=0, max_value=600, value=90, step=15, key="deng_tempo")
            
        if st.button("Calcular Risco Incisional", key="btn_deng"):
            res, contribs = calcular_risco_deng(deng_idade, deng_diabetes, deng_exposta, deng_albumina, deng_tempo)
            st.session_state.foot_ankle_id_res = (res, contribs, "deng")
            params_str = f"Idade: {deng_idade} | Diabetes: {deng_diabetes} | Exposta: {deng_exposta} | Albumin<35: {deng_albumina} | Tempo: {deng_tempo} min"
            salvar_registro("Infecção Fratura Tornozelo", res, "complicacao", params_str)

        if st.session_state.get('foot_ankle_id_res') and st.session_state.foot_ankle_id_res[2] == "deng":
            res, contribs = st.session_state.foot_ankle_id_res[0], st.session_state.foot_ankle_id_res[1]
            col_g, col_x = st.columns([1, 1.5])
            with col_g: 
                st.plotly_chart(gerar_grafico_velocimetro(res, "risco"), use_container_width=True)
            with col_x: 
                st.markdown("##### 🧠 Explicabilidade do Algoritmo (XAI)")
                if sum(contribs.values()) == 0:
                    st.success("🟢 **Risco Mínimo:** O paciente não apresenta nenhum dos fatores de risco mapeados pelo nomograma.")
                else:
                    st.markdown(obter_texto_explicativo(contribs))
                st.plotly_chart(gerar_grafico_waterfall(contribs, titulo="Impacto dos Fatores (Score de Risco)"), use_container_width=True)
                
        with st.expander("📚 Referência Científica"):
            st.markdown("""
            **Deng GH.** Construction and validation of a nomogram prediction model for postoperative incisional infection in ankle fractures. *Medicine*. 2023;102:48(e36408).  
            **DOI:** [10.1097/MD.0000000000036408](https://doi.org/10.1097/MD.0000000000036408)
            """)
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.markdown("<div class='input-card'><h4>🦶 Risco de Reintervenção por Infecção (I&D)</h4>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Dados do Paciente")
            fa_tabagismo = st.toggle("O paciente é fumante atual?", key="fa_tab")
            fa_diabetes = st.toggle("O paciente possui diagnóstico de Diabetes?", key="fa_diab")
        with c2:
            st.markdown("##### Dados Cirúrgicos")
            fa_tempo = st.number_input("Tempo estimado da cirurgia (minutos):", min_value=0, max_value=600, value=45, step=15, key="fa_tempo")
            
        if st.button("Calcular Risco de I&D (90 dias)", key="btn_bonsignore"):
            res, contribs = calcular_risco_bonsignore(fa_tabagismo, fa_diabetes, fa_tempo)
            st.session_state.foot_ankle_id_res = (res, contribs, "bonsignore")
            params_str = f"Tabagismo: {'Sim' if fa_tabagismo else 'Não'} | Diabetes: {'Sim' if fa_diabetes else 'Não'} | Tempo: {fa_tempo} min"
            salvar_registro("Risco I&D (Pé/Tornozelo)", res, "complicacao", params_str)
            
        if st.session_state.get('foot_ankle_id_res') and st.session_state.foot_ankle_id_res[2] == "bonsignore":
            res, contribs = st.session_state.foot_ankle_id_res[0], st.session_state.foot_ankle_id_res[1]
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
