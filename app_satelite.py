import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import requests
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from shapely.geometry import shape, Point
import scipy.ndimage  # Para suavizar o mapa e tirar o quadriculado

# --- 1. CONFIGURAÇÃO INICIAL ---
st.set_page_config(layout="wide", page_title="Tríade Agro Estratégica")

# Paleta Profissional Vibrante (Padrão de Mercado)
agri_vibrante = [
    [0.0, 'rgb(215,48,39)'],   # Vermelho (Solo/Estresse)
    [0.2, 'rgb(252,141,89)'],  # Laranja
    [0.4, 'rgb(254,224,139)'], # Amarelo (Transição)
    [0.6, 'rgb(166,217,106)'], # Verde Claro
    [0.8, 'rgb(26,152,80)'],   # Verde
    [1.0, 'rgb(0,68,27)']      # Verde Escuro (Vigor Máximo)
]

# Função de Autenticação Copernicus CDSE
def get_copernicus_token():
    try:
        client_id = st.secrets["SH_CLIENT_ID"]
        client_secret = st.secrets["SH_CLIENT_SECRET"]
        url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
        data = {"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret}
        response = requests.post(url, data=data)
        return response.json().get("access_token")
    except:
        return None

if "logado" not in st.session_state:
    st.session_state.logado = False

# --- 2. TELA DE LOGIN ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛰️ Tríade Satélite v1.0</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        senha = st.text_input("Senha de Acesso", type="password")
        if st.button("ACESSAR PLATAFORMA"):
            if senha == "triade2026":
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Senha Incorreta")

# --- 3. DASHBOARD PRINCIPAL ---
else:
    with st.sidebar:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        st.header("⚙️ Filtros de Análise")
        f_geo = st.file_uploader("Contorno do Talhão (.json)", type=['geojson', 'json'])
        
        st.divider()
        st.date_input("Data Inicial", value=pd.to_datetime("2026-01-01"))
        st.date_input("Data Final", value=pd.to_datetime("2026-01-30"))
        
        if st.button("Sair"):
            st.session_state.logado = False
            st.rerun()

    if f_geo:
        try:
            geojson_data = json.load(f_geo)
            # Processamento da Geometria
            if 'features' in geojson_data:
                geom = shape(geojson_data['features'][0]['geometry'])
            else:
                geom = shape(geojson_data)
            
            minx, miny, maxx, maxy = geom.bounds
            path_coords = list(geom.exterior.coords) if hasattr(geom, 'exterior') else list(geom[0].exterior.coords)

            # --- GALERIA DE MINIATURAS ---
            st.subheader("🖼️ Galeria de Imagens Disponíveis")
            m1, m2, m3 = st.columns(3)
            datas_disponiveis = ["30/01/2026", "22/01/2026", "15/01/2026"]
            
            if "data_ativa" not in st.session_state:
                st.session_state.data_ativa = datas_disponiveis[0]

            for i, col in enumerate([m1, m2, m3]):
                with col:
                    st.caption(f"Satélite: Sentinel-2")
                    if st.button(f"📅 {datas_disponiveis[i]}", key=f"btn_{i}"):
                        st.session_state.data_ativa = datas_disponiveis[i]

            st.divider()

            # --- GERAÇÃO DO MAPA SUAVIZADO ---
            res = 120 # Resolução da matriz
            x = np.linspace(minx, maxx, res)
            y = np.linspace(miny, maxy, res)
            X, Y = np.meshgrid(x,
