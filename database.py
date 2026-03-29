import sqlite3
import pandas as pd
import datetime
import streamlit as st

DB_NAME = "ilizarov_database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS avaliacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT,
            prontuario TEXT,
            paciente TEXT,
            mae TEXT,
            avaliacao_clinica TEXT,
            parametros TEXT,
            resultado REAL,
            classificacao TEXT,
            tipo TEXT
        )
    ''')
    conn.commit()
    conn.close()

def obter_classificacao(prob, tipo):
    if tipo == "complicacao":
        if prob < 5: return ("Baixo Risco", "green")
        elif prob < 20: return ("Risco Moderado", "orange")
        else: return ("Alto Risco", "red")
    elif tipo == "melhora":
        if prob >= 80: return ("Excelente", "green")
        elif prob >= 60: return ("Aceitável", "orange")
        else: return ("Inadequado", "red")
    else:
        if prob < 30: return ("Baixo Risco", "green")
        elif prob < 60: return ("Risco Moderado", "orange")
        else: return ("Alto Risco", "red")

def salvar_registro(mod, prob, tipo, parametros=""):
    # Verifica se há paciente logado para evitar erros de sessão
    if 'paciente_ativo' not in st.session_state or not st.session_state.paciente_ativo.get('nome'):
        return False
        
    pac = st.session_state.paciente_ativo['nome']
    mae = st.session_state.paciente_ativo['mae']
    pront = str(st.session_state.paciente_ativo['prontuario'])
    classif, _ = obter_classificacao(prob, tipo)
    data = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO avaliacoes (data_hora, prontuario, paciente, mae, avaliacao_clinica, parametros, resultado, classificacao, tipo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (data, pront, pac, mae, mod, parametros, round(prob, 1), classif, tipo))
    conn.commit()
    conn.close()
    return True

def obter_df_paciente(prontuario):
    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT data_hora as "Data/Hora", avaliacao_clinica as "Avaliação Clínica", parametros as "Parâmetros Inseridos", 
               resultado as "Resultado (%)", classificacao as "Classificação", tipo as "Tipo"
        FROM avaliacoes WHERE prontuario = ?
    '''
    df = pd.read_sql(query, conn, params=(str(prontuario),))
    conn.close()
    return df

def obter_df_completo():
    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT data_hora as "Data/Hora", prontuario as "Prontuário", paciente as "Paciente", mae as "Mãe",
               avaliacao_clinica as "Avaliação Clínica", parametros as "Parâmetros Inseridos", 
               resultado as "Resultado (%)", classificacao as "Classificação", tipo as "Tipo"
        FROM avaliacoes
    '''
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def excluir_prontuario(prontuario):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Exclui todos os registros vinculados àquele número de prontuário
    c.execute('DELETE FROM avaliacoes WHERE prontuario = ?', (str(prontuario),))
    conn.commit()
    conn.close()
    return True
