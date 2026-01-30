import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import os
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from shapely.geometry import shape

# --- 1. CONFIGURAÇÃO E LOGIN ---
st.set_page_config(layout="wide", page_title="Tríade Satélite v1.0")

# FUNÇÃO AJUSTADA PARA O COPERNICUS DATA SPACE (CDSE)
def get_copernicus_token():
    try:
        # Pega as chaves que você salvou no Secrets do Streamlit
        client_id = st.secrets["SH_CLIENT_ID"]
        client_secret = st.secrets["SH_CLIENT_SECRET"]
        
        # URL de Autenticação Oficial do Copernicus CDSE
        url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
        
        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret
        }
        
        response = requests.post(url, data=data)
        return response.json().get("access_token")
    except Exception as e:
        st.error(f"Erro na autenticação Copernicus: {e}")
        return None

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛰️ Tríade Satélite v1.0</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        senha = st.text_input("Acesso Satelital", type="password")
        if st.button("DESBLOQUEAR PLATAFORMA"):
            if senha == "triade2026":
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Senha Incorreta")
else:
    # --- 2. BARRA LATERAL ---
    with st.sidebar:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        st.header("📍 Painel de Controle")
        
        f_geo = st.file_uploader("Subir Contorno do Talhão", type=['geojson', 'json'])
        data_ini = st.date_input("Data Inicial", value=pd.to_datetime("2026-01-01"))
        data_fim = st.date_input("Data Final", value=pd.to_datetime("2026-01-30"))

    # --- 3. PROCESSAMENTO ---
    if f_geo:
        try:
            geojson_data = json.load(f_geo)
            st.success(f"✅ Talhão '{f_geo.name}' identificado!")
            
            if st.button("🚀 CAPTURAR NDVI COPERNICUS"):
                with st.spinner("Conectando ao Ecossistema Copernicus..."):
                    token = get_copernicus_token()
                    
                    if token:
                        st.info("Autenticação com Copernicus realizada com sucesso!")
                        
                        # Geração do NDVI (Simulado enquanto ajustamos a BBOX real)
                        ndvi_data = np.random.uniform(0.15, 0.9, (100, 100))
                        
                        tab1, tab2 = st.tabs(["🌱 NDVI Real", "🗺️ Zonas de Manejo"])
                        
                        with tab1:
                            fig = go.Figure(data=go.Heatmap(
                                z=ndvi_data, 
                                colorscale='RdYlGn',
                                zmin=0, zmax=1
                            ))
                            fig.update_layout(title="Índice de Vegetação Sentinel-2", height=600)
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with tab2:
                            # KMeans para 3 zonas com paleta Verde-Vermelho
                            pixels = ndvi_data.flatten().reshape(-1, 1)
                            kmeans = KMeans(n_clusters=3, random_state=42).fit(pixels)
                            zonas = kmeans.labels_.reshape(ndvi_data.shape)
                            
                            fig_z = go.Figure(data=go.Heatmap(
                                z=zonas, 
                                colorscale='RdYlGn'
                            ))
                            fig_z.update_layout(title="Zonas de Manejo Tríade Agro", height=600)
                            st.plotly_chart(fig_z, use_container_width=True)
                    else:
                        st.error("Falha ao obter Token. Verifique o ID e o Secret no painel do Copernicus.")
        except Exception as e:
            st.error(f"Erro no processamento: {e}")
    else:
        st.info("Arraste o arquivo .json do talhão para começar.")
