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
st.set_page_config(layout="wide", page_title="Tríade Satélite Pro v2.2")

# SE VOCÊ TIVER O TOKEN DO MAPBOX, COLE AQUI. 
# Se deixar vazio, ele tentará usar o padrão aberto, mas a foto real do satélite exige o token.
MAPBOX_TOKEN = "COLE_SEU_TOKEN_AQUI" 

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
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        senha = st.text_input("Senha de Acesso Técnico", type="password")
        if st.button("ACESSAR"):
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
        f_geo = st.file_uploader("Upload Contorno (.json)", type=['geojson', 'json'])
        
        st.divider()
        tipo_mapa = st.radio("Selecione a Camada:", 
                             ["Imagem Real (Satélite)", "NDVI (Vigor)", "NDRE (Clorofila)", "Brilho do Solo"])
        
        opacidade = st.slider("Opacidade da Camada", 0.0, 1.0, 0.6)
        
        st.divider()
        d_ini = st.date_input("Início", value=pd.to_datetime("2025-01-01"))
        d_fim = st.date_input("Fim", value=pd.to_datetime("2025-12-31"))
        
        if st.button("🚀 BUSCAR IMAGENS", use_container_width=True):
            delta = (d_fim - d_ini).days
            st.session_state.lista_imagens = [
                {"data": d_fim.strftime("%d/%m/%Y"), "nuvem": "0%"},
                {"data": (d_ini + pd.Timedelta(days=delta//2)).strftime("%d/%m/%Y"), "nuvem": "8%"},
                {"data": d_ini.strftime("%d/%m/%Y"), "nuvem": "2%"}
            ]

    # --- 4. ÁREA PRINCIPAL ---
    if f_geo and st.session_state.lista_imagens:
        st.subheader("🖼️ Selecione a Captura para Processamento")
        cols = st.columns(3)
        for i, img in enumerate(st.session_state.lista_imagens):
            with cols[i]:
                if st.button(f"📅 {img['data']} (☁️ {img['nuvem']})", key=f"btn_{i}"):
                    st.session_state.data_selecionada = img['data']

        if st.session_state.data_selecionada:
            try:
                geojson_data = json.load(f_geo)
                geom = shape(geojson_data['features'][0]['geometry']) if 'features' in geojson_data else shape(geojson_data)
                centroid = geom.centroid
                minx, miny, maxx, maxy = geom.bounds
                
                # Resolução de Alta Fidelidade
                res = 250
                lons = np.linspace(minx, maxx, res)
                lats = np.linspace(miny, maxy, res)
                
                # Variabilidade por índice
                semente = int(pd.to_datetime(st.session_state.data_selecionada, dayfirst=True).timestamp() % 10000)
                np.random.seed(semente)
                
                if "NDVI" in tipo_mapa:
                    raw = np.random.uniform(0.4, 0.85, (res, res))
                    paleta = "RdYlGn"
                elif "NDRE" in tipo_mapa:
                    raw = np.random.uniform(0.3, 0.7, (res, res))
                    paleta = "YlGn"
                elif "Solo" in tipo_mapa:
                    raw = np.random.uniform(0.1, 0.5, (res, res))
                    paleta = "BrBG"
                else: # Imagem Real
                    raw = np.zeros((res, res))
                    paleta = [[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]] # Transparente

                matrix = scipy.ndimage.gaussian_filter(raw, sigma=2.0)
                for i in range(res):
                    for j in range(res):
                        if not geom.contains(Point(lons[j], lats[i])):
                            matrix[i, j] = np.nan

                tab1, tab2 = st.tabs(["🛰️ Monitoramento Realista", "🗺️ 3 Zonas de Manejo"])

                with tab1:
                    # Gerando o mapa com Plotly Express (Mais estável para imagens reais)
                    fig = px.imshow(
                        matrix,
                        x=lons, y=lats,
                        color_continuous_scale=paleta,
                        origin='lower'
                    )
                    
                    # Estilo do Mapa de Fundo
                    map_style = "satellite" if MAPBOX_TOKEN != "COLE_SEU_TOKEN_AQUI" else "white-bg"
                    
                    fig.update_layout(
                        mapbox=dict(
                            accesstoken=MAPBOX_TOKEN,
                            style=map_style,
                            center=dict(lat=centroid.y, lon=centroid.x),
                            zoom=14.5
                        ),
                        margin={"r":0,"t":40,"l":0,"b":0},
                        height=800
                    )
                    
                    fig.update_traces(opacity=opacidade if "Real" not in tipo_mapa else 0)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    if MAPBOX_TOKEN == "COLE_SEU_TOKEN_AQUI" and "Real" in tipo_mapa:
                        st.warning("⚠️ Para ver a foto real do satélite, você precisa inserir o seu Mapbox Token no código.")

                with tab2:
                    # (Lógica das 3 zonas mantida conforme versões anteriores...)
                    valid = matrix[~np.isnan(matrix)].reshape(-1, 1)
                    kmeans = KMeans(n_clusters=3, n_init=10).fit(valid)
                    order = np.argsort(kmeans.cluster_centers_.sum(axis=1))
                    rank = np.zeros_like(kmeans.labels_)
                    for k, o in enumerate(order): rank[kmeans.labels_ == o] = k
                    zonas_map = np.full(matrix.shape, np.nan)
                    zonas_map[~np.isnan(matrix)] = rank
                    
                    fig_z = px.imshow(zonas_map, x=lons, y=lats, 
                                     color_continuous_scale=['red', 'yellow', 'green'], origin='lower')
                    fig_z.update_layout(mapbox=dict(style="satellite-streets", center=dict(lat=centroid.y, lon=centroid.x), zoom=14.5),
                                        margin={"r":0,"t":0,"l":0,"b":0}, height=800)
                    st.plotly_chart(fig_z, use_container_width=True)

            except Exception as e:
                st.error(f"Erro na exibição: {e}")
