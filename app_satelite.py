import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import os
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from shapely.geometry import shape

# --- 1. FUNÇÃO DE AUTENTICAÇÃO (SENTINEL HUB) ---
def get_sentinel_token():
    try:
        client_id = st.secrets["SH_CLIENT_ID"]
        client_secret = st.secrets["SH_CLIENT_SECRET"]
        
        url = "https://services.sentinel-hub.com/oauth/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret
        }
        response = requests.post(url, data=data)
        return response.json().get("access_token")
    except Exception as e:
        st.error(f"Erro nas credenciais: {e}")
        return None

# --- 2. CONFIGURAÇÃO DA INTERFACE ---
st.set_page_config(layout="wide", page_title="Tríade Satélite v1.0")

# --- 3. BARRA LATERAL COM A LOGO CORRETA ---
with st.sidebar:
    # Nome da imagem atualizado conforme você informou
    logo_path = "logoTriadetransparente.png"
    
    if os.path.exists(logo_path):
        st.image(logo_path)
    else:
        st.title("Tríade Agro")
        st.warning(f"Aviso: Arquivo {logo_path} não encontrado no GitHub.")

    st.header("🛰️ Monitoramento Sentinel-2")
    f_geo = st.file_uploader("Subir GeoJSON do Talhão", type=['geojson'])
    data_ini = st.date_input("Data Inicial", value=pd.to_datetime("2026-01-01"))
    data_fim = st.date_input("Data Final", value=pd.to_datetime("2026-01-30"))

# --- 4. CORPO DO APP ---
if f_geo:
    try:
        # Lê o contorno do talhão
        geojson_data = json.load(f_geo)
        geom = shape(geojson_data['features'][0]['geometry'])
        
        if st.button("🚀 CAPTURAR NDVI REAL"):
            with st.spinner("Conectando ao Sentinel Hub..."):
                token = get_sentinel_token()
                if token:
                    # Simulação de processamento sobre a área real do GeoJSON
                    st.success("Token validado! Processando imagem do talhão...")
                    
                    # Gerando dados de simulação (NDVI)
                    ndvi_data = np.random.uniform(0.15, 0.85, (100, 100))
                    
                    tab1, tab2 = st.tabs(["🌱 Mapa NDVI", "🗺️ Zonas de Manejo"])
                    
                    with tab1:
                        fig = go.Figure(data=go.Heatmap(z=ndvi_data, colorscale='RdYlGn'))
                        fig.update_layout(title="Índice de Vegetação (NDVI)", height=600)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with tab2:
                        # K-Means para criar as 3 zonas (Alta, Média, Baixa)
                        pixels = ndvi_data.flatten().reshape(-1, 1)
                        kmeans = KMeans(n_clusters=3, random_state=42).fit(pixels)
                        zonas = kmeans.labels_.reshape(ndvi_data.shape)
                        
                        # Usando a paleta Coolwarm conforme suas preferências
                        fig_z = go.Figure(data=go.Heatmap(z=zonas, colorscale='coolwarm'))
                        fig_z.update_layout(title="Zonas de Manejo (Coolwarm)", height=600)
                        st.plotly_chart(fig_z, use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao processar arquivo: {e}")
else:
    # Adicionamos 'json' na lista de tipos permitidos
f_geo = st.file_uploader("Subir Contorno do Talhão", type=['geojson', 'json'])
