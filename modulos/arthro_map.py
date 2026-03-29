import streamlit as st
from utils import gerar_grafico_velocimetro, gerar_grafico_waterfall, obter_texto_explicativo
from database import salvar_registro

def calcular_risco(fc, perda_sangue, ureia, procedimento, raca, asa, comorbidade, fratura):
    pontos = 0.0
    contribs = {}
    
    c_fc = fc * (80.0 / 120.0) 
    contribs["Freq. Cardíaca"] = round(c_fc, 1)
    pontos += c_fc
    
    c_sangue = perda_sangue * (98.0 / 4000.0)
    contribs["Perda Sangue"] = round(c_sangue, 1)
    pontos += c_sangue
    
    c_ureia = ureia * (100.0 / 100.0)
    contribs["Ureia"] = round(c_ureia, 1)
    pontos += c_ureia
    
    c_proc = 0
    if procedimento == "Parcial": c_proc = 16
    elif procedimento == "Revisão": c_proc = 29
    contribs["Procedimento"] = c_proc
    pontos += c_proc
    
    c_raca = 28 if raca == "Branco" else 0
    contribs["Raça"] = c_raca
    pontos += c_raca
    
    c_asa = 29 if asa == "ASA > 2 (III, IV, V)" else 0
    contribs["ASA"] = c_asa
    pontos += c_asa
    
    c_com = 0
    if comorbidade == "Pulmonar": c_com = 16
    elif comorbidade == "Cardiovascular": c_com = 34
    elif comorbidade == "Diabetes": c_com = 38
    contribs["Comorbidades"] = c_com
    pontos += c_com
    
    c_frat = 65 if fratura else
