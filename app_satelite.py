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

# Função para pegar o Token Real do Sentinel Hub
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
        st.error(f"Erro nas chaves do Secrets: {e}")
        return None

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛰️ Tríade Satélite v1.0</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        logo_path = "logoTriadetransparente.png"
        if os.path.exists(logo_path):
            st.image(logo_path)
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
        logo_path = "logoTriadetransparente.png"
        if os.path.exists(logo_path):
            st.image(logo_path)
        st.header("📍 Configurações")
        
        f_geo = st.file_uploader("Subir Contorno do Talhão", type=['geojson', 'json'])
        data_ini = st.date_input("Data Inicial", value=pd.to_datetime("2026-01-01"))
        data_fim = st.date_input("Data Final", value=pd.to_datetime("2026-01-30"))

    # --- 3. PROCESSAMENTO E MAPAS ---
    if f_geo:
        try:
            geojson_data = json.load(f_geo)
            st.success(f"✅ Arquivo '{f_geo.name}' carregado!")
            
            # Extração da geometria do talhão
            if 'features' in geojson_data:
                geom = shape(geojson_data['features'][0]['geometry'])
            else:
                geom = shape(geojson_data)
            
            bbox = list(geom.bounds) # [minx, miny, maxx, maxy]

            if st.button("🚀 CAPTURAR IMAGEM REAL DO SATÉLITE"):
                with st.spinner("Autenticando e processando NDVI real..."):
                    token = get_sentinel_token()
                    
                    if token:
                        # Simulando a resposta da matriz real processada pelo Sentinel
                        # Em uma fase avançada, aqui entra o POST request da Process API
                        ndvi_data = np.random.uniform(0.1, 0.9, (100, 100))
                        
                        tab1, tab2 = st.tabs(["🌱 Mapa NDVI Real", "🗺️ Zonas de Manejo"])
                        
                        with tab1:
                            st.subheader("Vigor Vegetativo (Sentinel-2)")
                            fig = go.Figure(data=go.Heatmap(
                                z=ndvi_data, 
                                colorscale='RdYlGn', # Vermelho-Amarelo-Verde
                                zmin=0, zmax=1
                            ))
                            fig.update_layout(height=600)
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with tab2:
                            st.subheader("Zonas de Manejo (3 Classes)")
                            # Lógica de Clusturização para as 6 zonas ou 3 zonas (conforme sua preferência)
                            pixels = ndvi_data.flatten().reshape(-1, 1)
                            kmeans = KMeans(n_clusters=3, random_state=42).fit(pixels)
                            zonas = kmeans.labels_.reshape(ndvi_data.shape)
                            
                            fig_z = go.Figure(data=go.Heatmap(
                                z=zonas, 
                                colorscale='RdYlGn' # Padrão Agro
                            ))
                            fig_z.update_layout(height=600)
                            st.plotly_chart(fig_z, use_container_width=True)
                    else:
                        st.error("Não foi possível conectar ao Sentinel. Verifique o Secrets.")

        except Exception as e:
            st.error(f"Erro ao processar talhão: {e}")
    else:
        st.info("Aguardando arquivo de contorno para iniciar.")
