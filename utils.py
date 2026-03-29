import plotly.graph_objects as go
import streamlit as st

def carregar_css():
    st.markdown("""
    <style>
        .login-box { background-color: var(--secondary-background-color); border-radius: 24px; border: 1px solid rgba(128, 128, 128, 0.15); padding: 50px; box-shadow: 0 15px 35px rgba(0, 0, 0, 0.15); text-align: center; max-width: 500px; margin: auto; color: var(--text-color); }
        .watermark { position: fixed; bottom: 20px; right: 30px; opacity: 0.5; font-family: 'Georgia', serif; font-style: italic; font-size: 0.9rem; pointer-events: none; color: var(--text-color); }
        .main-title { background: -webkit-linear-gradient(45deg, #1b5e20, #4caf50); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; font-size: 3.5rem; text-align: center; letter-spacing: -1px; }
        .ilizarov-text { font-family: 'Georgia', serif; font-style: italic; color: #4caf50; margin-left: 10px; }
        .patient-header { background: linear-gradient(135deg, #1b5e20, #4caf50); color: white; padding: 25px 35px; border-radius: 20px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 10px 30px rgba(27, 94, 32, 0.2); }
        .dashboard-card { background-color: var(--secondary-background-color); border-radius: 16px; padding: 24px; box-shadow: 0 8px 24px rgba(0,0,0,0.06); text-align: left; border-left: 8px solid #ddd; color: var(--text-color); transition: all 0.3s ease; display: flex; flex-direction: column; justify-content: space-between; }
        .dashboard-card:hover { transform: translateY(-4px); box-shadow: 0 12px 32px rgba(0,0,0,0.1); }
        .card-value { font-size: 2.5rem; font-weight: 800; margin: 10px 0; line-height: 1; }
        .b-green { border-left-color: #2e7d32 !important; } .t-green { color: #2e7d32 !important; }
        .b-orange { border-left-color: #ef6c00 !important; } .t-orange { color: #ef6c00 !important; }
        .b-red { border-left-color: #c62828 !important; } .t-red { color: #c62828 !important; }
        .input-card { background-color: var(--secondary-background-color); padding: 35px; border-radius: 20px; box-shadow: 0 8px 30px rgba(0,0,0,0.05); margin-top: 15px; color: var(--text-color); border: 1px solid rgba(128, 128, 128, 0.1); }
        .calc-info { background-color: rgba(76, 175, 80, 0.05); padding: 16px 20px; border-radius: 12px; border-left: 5px solid #4caf50; margin-bottom: 25px; font-size: 0.95rem; color: var(--text-color); box-shadow: 0 2px 10px rgba(0,0,0,0.02); }
        .sidebar-section-title { font-size: 0.75rem; font-weight: 700; color: #888; text-transform: uppercase; letter-spacing: 1.2px; margin-top: 20px; margin-bottom: 10px; }
        .sidebar-patient-card { background: rgba(76, 175, 80, 0.08); border-left: 4px solid #4caf50; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

def gerar_grafico_waterfall(contribuicoes, titulo="Impacto das Variáveis"):
    labels = list(contribuicoes.keys())
    values = list(contribuicoes.values())
    measures = ["relative"] * len(labels)
    labels.append("Pontuação Total")
    values.append(sum(values))
    measures.append("total")
    
    fig = go.Figure(go.Waterfall(
        orientation="v", measure=measures, x=labels, textposition="outside",
        text=[f"{v:+.1f}" if m == "relative" else f"{v:.1f}" for m, v in zip(measures, values)],
        y=values, connector={"line":{"color":"rgba(128,128,128,0.5)"}},
        decreasing={"marker":{"color":"#1b5e20"}}, increasing={"marker":{"color":"#ef6c00"}}, totals={"marker":{"color":"#333333"}}       
    ))
    fig.update_layout(title={"text": titulo, "font": {"size": 14}}, showlegend=False, height=320, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig

def gerar_grafico_velocimetro(prob, tipo="risco"):
    if tipo == "complicacao":
        steps = [{'range': [0, 5], 'color': "rgba(46, 125, 50, 0.8)"}, 
                 {'range': [5, 20], 'color': "rgba(239, 108, 0, 0.8)"}, 
                 {'range': [20, 100], 'color': "rgba(198, 40, 40, 0.8)"}]
    else:
        steps = [{'range': [0, 30], 'color': "rgba(46, 125, 50, 0.8)"}, 
                 {'range': [30, 60], 'color': "rgba(239, 108, 0, 0.8)"}, 
                 {'range': [60, 100], 'color': "rgba(198, 40, 40, 0.8)"}]

    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=prob, number={'suffix': "%", 'font': {'size': 40, 'color': '#333'}},
        domain={'x': [0, 1], 'y': [0, 1]}, title={'text': "Risco Estimado", 'font': {'size': 18, 'color': '#555'}},
        gauge={'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"}, 'bar': {'color': "rgba(0, 0, 0, 0.8)", 'thickness': 0.15}, 'bgcolor': "white", 'borderwidth': 2, 'bordercolor': "gray", 'steps': steps}
    ))
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor='rgba(0,0,0,0)')
    return fig

def obter_texto_explicativo(contribuicoes):
    contribs_clinicas = {k: v for k, v in contribuicoes.items()}
    if not contribs_clinicas: return ""
    max_var = max(contribs_clinicas, key=lambda k: contribs_clinicas[k])
    max_val = contribs_clinicas[max_var]
    if max_val == 0: return "Nenhum fator de risco adicional pontuou neste paciente."
    return f"A variável que mais **aumentou** a pontuação de risco neste paciente foi: **{max_var}** (+{max_val:.1f} pontos)."
