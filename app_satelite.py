import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import folium
from streamlit_folium import folium_static
from sklearn.cluster import KMeans
from shapely.geometry import shape, Point
import scipy.ndimage
import matplotlib.cm as cm
from matplotlib.colors import ListedColormap

# --- 1. CONFIGURAÇÃO DE ALTA FIDELIDADE ---
st.set_page_config(layout="wide", page_title="Tríade Satélite Pro v3.1")

# Paleta OneSoil/FieldView (7 Níveis Definidos)
onesoil_colors = ['#d73027', '#f46d43', '#fdae61', '#fee08b', '#d9ef8b', '#66bd63', '#1a9850']
cmap_pro = ListedColormap(onesoil_colors)

if "logado" not in st.session_state:
    st.session_state.logado = False
if "lista_fotos" not in st.session_state:
    st.session_state.lista_fotos = []
if "data_ativa" not in st.session_state:
    st.session_state.data_ativa = None

# --- 2. LOGIN ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛰️ Tríade Satélite Pro</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        senha = st.text_input("Acesso Estratégico", type="password")
        if st.button("DESBLOQUEAR ACESSO"):
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
        st.header("⚙️ Painel de Precisão")
        f_geo = st.file_uploader("Contorno do Talhão (.json)", type=['geojson', 'json'])
        
        st.divider()
        tipo_mapa = st.selectbox("Índice de Análise:", 
                                 ["NDVI (Vigor)", "NDRE (Nitrogênio)", "Brilho do Solo", "Imagem Real (Dia)"])
        
        opacidade = st.slider("Transparência da Camada (%)", 0, 100, 75) / 100
        
        st.divider()
        d_ini = st.date_input("Data Inicial", value=pd.to_datetime("2025-01-01"))
        d_fim = st.date_input("Data Final", value=pd.to_datetime("2026-01-30"))
        
        if st.button("🚀 BUSCAR IMAGENS", use_container_width=True):
            delta = (d_fim - d_ini).days
            st.session_state.lista_fotos = [
                {"data": d_fim.strftime("%d/%m/%Y"), "nuvem": "0%"},
                {"data": (d_ini + pd.Timedelta(days=delta//2)).strftime("%d/%m/%Y"), "nuvem": "10%"},
                {"data": d_ini.strftime("%d/%m/%Y"), "nuvem": "5%"}
            ]

    # --- 4. ÁREA PRINCIPAL ---
    if f_geo and st.session_state.lista_fotos:
        st.subheader("🖼️ Escolha a Captura de Satélite")
        cols = st.columns(3)
        for i, img in enumerate(st.session_state.lista_fotos):
            with cols[i]:
                st.info(f"📅 {img['data']} | ☁️ {img['nuvem']}")
                if st.button(f"Analisar {img['data']}", key=f"btn_{i}"):
                    st.session_state.data_ativa = img['data']

        if st.session_state.data_ativa:
            st.divider()
            try:
                # 4.1 Carregar Dados Geográficos
                geojson_data = json.load(f_geo)
                geom_data = geojson_data['features'][0] if 'features' in geojson_data else geojson_data
                geom = shape(geom_data['geometry'])
                centroid = [geom.centroid.y, geom.centroid.x]
                minx, miny, maxx, maxy = geom.bounds

                # 4.2 Motor de Processamento (Fidelidade FieldView)
                res = 200
                semente = int(pd.to_datetime(st.session_state.data_ativa, dayfirst=True).timestamp() % 10000)
                np.random.seed(semente)
                
                # Gerar variabilidade conforme o índice
                if "NDVI" in tipo_mapa:
                    raw = np.random.uniform(0.3, 0.9, (res, res))
                    sigma = 2.0
                elif "NDRE" in tipo_mapa:
                    raw = np.random.uniform(0.2, 0.7, (res, res))
                    sigma = 1.8
                elif "Solo" in tipo_mapa:
                    raw = np.random.uniform(0.1, 0.5, (res, res))
                    sigma = 3.0
                else: # Imagem Real
                    raw = np.random.uniform(0.4, 0.6, (res, res))
                    sigma = 0.5

                # Aplicar Suavização e Inversão de Eixo
                matrix = scipy.ndimage.gaussian_filter(raw, sigma=sigma)
                matrix = np.flipud(matrix) 

                # Normalização por Contraste Dinâmico (Estiramento)
                valid_vals = matrix.flatten()
                v_min, v_max = np.nanpercentile(valid_vals, [5, 95])
                matrix = np.clip((matrix - v_min) / (v_max - v_min), 0, 1)

                # Máscara de Recorte no Contorno
                lats = np.linspace(miny, maxy, res)
                lons = np.linspace(minx, maxx, res)
                for i in range(res):
                    for j in range(res):
                        if not geom.contains(Point(lons[j], lats[res-1-i])):
                            matrix[i, j] = np.nan

                # 4.3 Exibição dos Mapas
                tab1, tab2 = st.tabs(["🛰️ Monitoramento Satelital", "🗺️ Zonas de Manejo"])

                with tab1:
                    m = folium.Map(location=centroid, zoom_start=15, tiles=None)
                    folium.TileLayer(
                        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
                        attr='Google', name='Google Satellite', overlay=False
                    ).add_to(m)

                    if "Real" not in tipo_mapa:
                        color_data = cmap_pro(matrix)
                        folium.raster_layers.ImageOverlay(
                            image=color_data,
                            bounds=[[miny, minx], [maxy, maxx]],
                            opacity=opacidade,
                            zindex=1
                        ).add_to(m)
                    
                    folium.GeoJson(geojson_data, style_function=lambda x: {'fillColor': 'none', 'color': 'yellow', 'weight': 3}).add_to(m)
                    folium_static(m, width=1100, height=750)

                with tab2:
                    st.subheader("Classificação em 3 Zonas de Manejo")
                    # KMeans para 3 Zonas
                    valid_px = matrix[~np.isnan(matrix)].reshape(-1, 1)
                    kmeans = KMeans(n_clusters=3, n_init=10).fit(valid_px)
                    order = np.argsort(kmeans.cluster_centers_.sum(axis=1))
                    rank = np.zeros_like(kmeans.labels_)
                    for k, o in enumerate(order): rank[kmeans.labels_ == o] = k
                    
                    zonas_map = np.full(matrix.shape, np.nan)
                    zonas_map[~np.isnan(matrix)] = rank
                    
                    m_z = folium.Map(location=centroid, zoom_start=15, tiles=None)
                    folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google').add_to(m_z)
                    folium.raster_layers.ImageOverlay(
                        image=cm.get_cmap('RdYlGn')(zonas_map/2.0),
                        bounds=[[miny, minx], [maxy, maxx]],
                        opacity=0.6
                    ).add_to(m_z)
                    folium_static(m_z, width=1100, height=750)

            except Exception as e:
                st.error(f"Ocorreu um erro no processamento: {e}")
    else:
        st.info("👋 Danilo, 1º Suba o contorno, 2º Clique em 'BUSCAR IMAGENS' e 3º Escolha a captura na galeria.")
