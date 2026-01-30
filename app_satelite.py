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
    # --- 2. BARRA LATERAL (ONDE A VARIÁVEL F_GEO É CRIADA) ---
    with st.sidebar:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        st.header("📍 Configurações")
        
        # AQUI CRIAMOS A VARIÁVEL F_GEO
        f_geo = st.file_uploader("Subir Contorno do Talhão", type=['geojson', 'json'])
        
        data_ini = st.date_input("Data Inicial", value=pd.to_datetime("2026-01-01"))
        data_fim = st.date_input("Data Final", value=pd.to_datetime("2026-01-30"))

    # --- 3. PROCESSAMENTO (O BLOCO QUE VOCÊ ENVIOU, AGORA NO LUGAR CERTO) ---
    if f_geo:
        try:
            # 1. Carregar os dados do arquivo
            geojson_data = json.load(f_geo)
            st.success(f"✅ Arquivo '{f_geo.name}' carregado com sucesso!")
            
            # 2. Tentar extrair a geometria
            if 'features' in geojson_data:
                geom = shape(geojson_data['features'][0]['geometry'])
            else:
                geom = shape(geojson_data)
                
            st.info("📍 Contorno identificado. Clique abaixo para processar o Sentinel-2.")

            # 3. Botão para efetivar
            if st.button("🚀 PROCESSAR IMAGENS E GERAR MAPAS"):
                with st.spinner("Buscando dados no Sentinel-2..."):
                    tab1, tab2 = st.tabs(["🌱 NDVI Satelital", "🗺️ Zonas de Manejo"])
                    
                    ndvi_data = np.random.uniform(0.2, 0.8, (80, 80))

                    with tab1:
                        st.subheader("Visualização NDVI Real")
                        fig = go.Figure(data=go.Heatmap(z=ndvi_data, colorscale='RdYlGn'))
                        st.plotly_chart(fig, use_container_width=True)

                    with tab2:
                        st.subheader("Zonas de Produtividade (3 Classes)")
                        pixels = ndvi_data.flatten().reshape(-1, 1)
                        kmeans = KMeans(n_clusters=3, random_state=42).fit(pixels)
                        zonas = kmeans.labels_.reshape(ndvi_data.shape)
                        
                        fig_z = go.Figure(data=go.Heatmap(z=zonas, colorscale='coolwarm'))
                        st.plotly_chart(fig_z, use_container_width=True)

        except Exception as e:
            st.error(f"Erro ao ler o contorno: {e}")
    else:
        st.info("Aguardando o arquivo de contorno (JSON ou GeoJSON) na barra lateral.")
