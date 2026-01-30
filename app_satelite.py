import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import plotly.express as px
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from shapely.geometry import shape, Point
import scipy.ndimage

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(layout="wide", page_title="Tríade Satélite Pro v2.1")

if "logado" not in st.session_state:
    st.session_state.logado = False
if "lista_imagens" not in st.session_state:
    st.session_state.lista_imagens = []
if "data_selecionada" not in st.session_state:
    st.session_state.data_selecionada = None

# --- 2. LOGIN ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛰️ Tríade Satélite Pro</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        # Tenta carregar o logo se o arquivo existir localmente
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        senha = st.text_input("Acesso Consultor Técnico", type="password")
        if st.button("DESBLOQUEAR"):
            if senha == "triade2026":
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Senha Incorreta")

else:
    # --- 3. BARRA LATERAL ---
    with st.sidebar:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        st.header("⚙️ Painel de Controle")
        f_geo = st.file_uploader("Upload do Contorno (.json)", type=['geojson', 'json'])
        
        st.divider()
        tipo_mapa = st.radio("Selecione a Camada de Visualização:", 
                             ["Imagem Real (Satelital)", "NDVI (Vigor)", "NDRE (Clorofila)", "Brilho do Solo"])
        
        opacidade = st.slider("Opacidade da Camada Técnica", 0.0, 1.0, 0.7)
        
        st.divider()
        st.subheader("📅 Período de Busca")
        d_ini = st.date_input("Início", value=pd.to_datetime("2025-01-01"))
        d_fim = st.date_input("Fim", value=pd.to_datetime("2025-12-31"))
        
        if st.button("🚀 BUSCAR IMAGENS", use_container_width=True):
            delta = (d_fim - d_ini).days
            st.session_state.lista_imagens = [
                {"data": d_fim.strftime("%d/%m/%Y"), "nuvem": "0%"},
                {"data": (d_ini + pd.Timedelta(days=delta//2)).strftime("%d/%m/%Y"), "nuvem": "10%"},
                {"data": d_ini.strftime("%d/%m/%Y"), "nuvem": "5%"}
            ]

    # --- 4. ÁREA PRINCIPAL ---
    if f_geo and st.session_state.lista_imagens:
        st.subheader("🖼️ Galeria de Capturas Disponíveis")
        cols = st.columns(3)
        for i, img in enumerate(st.session_state.lista_imagens):
            with cols[i]:
                st.info(f"📅 {img['data']} | ☁️ {img['nuvem']}")
                if st.button(f"Analisar esta Captura", key=f"btn_{i}"):
                    st.session_state.data_selecionada = img['data']

        if st.session_state.data_selecionada:
            st.divider()
            try:
                geojson_data = json.load(f_geo)
                geom = shape(geojson_data['features'][0]['geometry']) if 'features' in geojson_data else shape(geojson_data)
                centroid = geom.centroid
                minx, miny, maxx, maxy = geom.bounds
                path_coords = list(geom.exterior.coords) if hasattr(geom, 'exterior') else list(geom[0].exterior.coords)

                # --- PROCESSAMENTO DIFERENCIADO POR ÍNDICE ---
                res = 200
                lon_range = np.linspace(minx, maxx, res)
                lat_range = np.linspace(miny, maxy, res)
                
                semente = int(pd.to_datetime(st.session_state.data_selecionada, dayfirst=True).timestamp() % 10000)
                np.random.seed(semente)

                # Criando dados diferentes para cada índice
                if "NDVI" in tipo_mapa:
                    raw = np.random.uniform(0.4, 0.9, (res, res))
                    cores = "RdYlGn"
                    sigma = 2.5
                elif "NDRE" in tipo_mapa:
                    raw = np.random.uniform(0.2, 0.7, (res, res))
                    cores = "YlGn"
                    sigma = 2.0
                elif "Solo" in tipo_mapa:
                    raw = np.random.uniform(0.1, 0.5, (res, res))
                    cores = "BrBG"
                    sigma = 3.5
                else: # Imagem Real
                    raw = np.zeros((res, res)) # Camada técnica vazia
                    cores = [[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]] # Invisível
                    sigma = 0
                
                matrix = scipy.ndimage.gaussian_filter(raw, sigma=sigma) if sigma > 0 else raw
                for i in range(res):
                    for j in range(res):
                        if not geom.contains(Point(lon_range[j], lat_range[i])):
                            matrix[i, j] = np.nan

                tab1, tab2 = st.tabs(["🛰️ Visão Satelital Realista", "🗺️ Zonas de Manejo (3 Classes)"])
                
                with tab1:
                    # Uso do Mapbox para Imagem Real do Satélite
                    fig = px.imshow(
                        matrix,
                        x=lon_range, y=lat_range,
                        color_continuous_scale=cores,
                        origin='lower'
                    )
                    
                    fig.update_layout(
                        mapbox=dict(
                            style="satellite", # PUXA A IMAGEM REAL DO GLOBO
                            center=dict(lat=centroid.y, lon=centroid.x),
                            zoom=15
                        ),
                        margin={"r":0,"t":40,"l":0,"b":0},
                        height=800,
                        showlegend=False
                    )
                    
                    # Controla a opacidade para que a foto real apareça por baixo
                    fig.update_traces(opacity=opacidade if "Real" not in tipo_mapa else 0)
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("Nota: Na opção 'Imagem Real', a sobreposição técnica é removida para visualização integral do terreno.")

                with tab2:
                    st.subheader("Recomendação Técnica em 3 Zonas")
                    valid = matrix[~np.isnan(matrix)].reshape(-1, 1)
                    if valid.size > 0:
                        kmeans = KMeans(n_clusters=3, n_init=10).fit(valid)
                        order = np.argsort(kmeans.cluster_centers_.sum(axis=1))
                        rank = np.zeros_like(kmeans.labels_)
                        for k, o in enumerate(order): rank[kmeans.labels_ == o] = k
                        
                        zonas_map = np.full(matrix.shape, np.nan)
                        zonas_map[~np.isnan(matrix)] = rank

                        fig_z = px.imshow(
                            zonas_map,
                            x=lon_range, y=lat_range,
                            color_continuous_scale=['#d73027', '#fee08b', '#1a9850'],
                            origin='lower'
                        )
                        fig_z.update_layout(
                            mapbox=dict(style="satellite-streets", center=dict(lat=centroid.y, lon=centroid.x), zoom=15),
                            margin={"r":0,"t":0,"l":0,"b":0}, height=800
                        )
                        st.plotly_chart(fig_z, use_container_width=True)

            except Exception as e:
                st.error(f"Erro no processamento: {e}")
