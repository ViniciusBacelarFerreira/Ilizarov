# app.py
import streamlit as st
from database import init_db, obter_df_paciente, obter_df_completo
import modulos.arthro_map as arthro_map
import modulos.nhfs as nhfs
import modulos.osteoporose as osteoporose
import modulos.start_back as start_back

# 1. Configuração e Login
st.set_page_config(page_title="OrtoPreditor Ilizarov", layout="wide")
init_db()

# ... Lógica de Login e Sidebar iguais às originais ...

# 2. Renderização das Abas
if nav == "🏠 Área de Trabalho" and st.session_state.paciente_ativo['prontuario']:
    tabs = st.tabs([
        "📊 Painel Visual", 
        "🦴 Artroplastia (Arthro-MAP)", 
        "🩼 Fratura de Fémur (NHFS)", 
        "🦴 Osteoporose (Lancet)", 
        "🏃 Dor Lombar (STarT Back)", 
        "📄 Relatório Oficial"
    ])

    with tabs[1]:
        arthro_map.renderizar_ui()
        
    with tabs[2]:
        nhfs.renderizar_ui()
        
    with tabs[3]:
        osteoporose.renderizar_ui()
        
    with tabs[4]:
        start_back.renderizar_ui()
