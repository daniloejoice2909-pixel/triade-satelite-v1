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
from matplotlib.colors import ListedColormap, BoundaryNorm

# --- 1. CONFIGURAÇÃO E PALETAS FIELDVIEW ---
st.set_page_config(layout="wide", page_title="Tríade Satélite Pro v2.7")

# Cores Exatas do FieldView (Do Vermelho Crítico ao Verde Escuro)
fieldview_colors = [
    '#d73027', # Baixíssimo
    '#f46d43', # Baixo
    '#fdae61', # Médio-Baixo
    '#fee08b', # Médio (Transição)
    '#d9ef8b', # Médio-Alto
    '#66bd63', # Alto
    '#1a9850'  # Altíssimo Vigor
]
cmap_fv = ListedColormap(fieldview_colors)

if "logado" not in st.session_state:
    st.session_state.logado = False
if "lista_fotos" not in st.session_state:
    st.session_state.lista_fotos = []

# --- 2. LOGIN ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛰️ Tríade Satélite Pro</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        senha = st.text_input("Acesso Consultor", type="password")
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
        st.header("⚙️ Painel de Precisão")
        f_geo = st.file_uploader("Contorno Berneck (.json)", type=['geojson', 'json'])
        
        st.divider()
        tipo_mapa = st.selectbox("Selecione o Índice Técnico:", 
                                 ["NDVI (Vigor de Safra)", "NDRE (Nitrogênio)", "Brilho do Solo", "Imagem Real (Dia)"])
        
        opacidade = st.slider("Opacidade da Camada (%)", 0, 100, 75) / 100
        
        st.divider()
        d_ini = st.date_input("Início", value=pd.to_datetime("2025-01-01"))
        d_fim = st.date_input("Fim", value=pd.to_datetime("2026-01-30"))
        
        if st.button("🚀 BUSCAR IMAGENS", use_container_width=True):
            delta = (d_fim - d_ini).days
            st.session_state.lista_fotos = [
                {"data": d_fim.strftime("%d/%m/%Y"), "nuvem": "0%"},
                {"data": (d_ini + pd.Timedelta(days=delta//2)).strftime("%d/%m/%Y"), "nuvem": "5%"},
                {"data": d_ini.strftime("%d/%m/%Y"), "nuvem": "10%"}
            ]

    # --- 4. ÁREA PRINCIPAL ---
    if f_geo and st.session_state.lista_fotos:
        st.subheader("🖼️ Galeria de Capturas Disponíveis")
        cols = st.columns(3)
        for i, img in enumerate(st.session_state.lista_fotos):
            with cols[i]:
                if st.button(f"📅 {img['data']} (☁️ {img['nuvem']})", key=f"btn_{i}"):
                    st.session_state.data_ativa = img['data']

        if "data_ativa" in st.session_state:
            try:
                geojson_data = json.load(f_geo)
                geom_data = geojson_data['features'][0] if 'features' in geojson_data else geojson_data
                geom = shape(geom_data['geometry'])
                centroid = [geom.centroid.y, geom.centroid.x]
                minx, miny, maxx, maxy = geom.bounds

                # --- MOTOR DE RENDERIZAÇÃO FIELDVIEW ---
                res = 180
                semente = int(pd.to_datetime(st.session_state.data_ativa, dayfirst=True).timestamp() % 10000)
                np.random.seed(semente)
                
                # Gera dados base
                raw = np.random.uniform(0.3, 0.9, (res, res))
                matrix = scipy.ndimage.gaussian_filter(raw, sigma=2.0)
                
                # RECORTE E CORREÇÃO DE POSIÇÃO
                matrix = np.flipud(matrix) 
                lat_arr = np.linspace(miny, maxy, res)
                lon_arr = np.linspace(minx, maxx, res)
                
                for i in range(res):
                    for j in range(res):
                        if not geom.contains(Point(lon_arr[j], lat_arr[res-1-i])):
                            matrix[i, j] = np.nan

                # Normalização por Percentil (O segredo do FieldView para dar contraste)
                valid_data = matrix[~np.isnan(matrix)]
                if valid_data.size > 0:
                    v_min, v_max = np.percentile(valid_data, [2, 98])
                    matrix = np.clip((matrix - v_min) / (v_max - v_min), 0, 1)

                tab1, tab2 = st.tabs(["🛰️ Monitoramento FieldView Style", "🗺️ 3 Zonas de Manejo"])

                with tab1:
                    m = folium.Map(location=centroid, zoom_start=15, tiles=None)
                    folium.TileLayer(
                        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
                        attr='Google Satellite', name='Google Satellite', overlay=False
                    ).add_to(m)

                    # Aplicando a Matriz de Cores Discretas (FieldView)
                    if "Real" not in tipo_mapa:
                        color_data = cmap_fv(matrix)
                        folium.raster_layers.ImageOverlay(
                            image=color_data,
                            bounds=[[miny, minx], [maxy, maxx]],
                            opacity=opacidade,
                            zindex=1
                        ).add_to(m)

                    folium.GeoJson(geojson_data, style_function=lambda x: {'fillColor': 'none', 'color': 'yellow', 'weight': 3}).add_to(m)
                    folium_static(m, width=1100, height=700)

                with tab2:
                    st.subheader("Mapa de Prescrição - 3 Zonas")
                    kmeans = KMeans(n_clusters=3, n_init=10).fit(valid_data.reshape(-1, 1))
                    order = np.argsort(kmeans.cluster_centers_.sum(axis=1))
                    rank = np.zeros_like(kmeans.labels_)
                    for k, o in enumerate(order): rank[kmeans.labels_ == o] = k
                    
                    zonas_map = np.full(matrix.shape, np.nan)
                    zonas_map[~np.isnan(matrix)] = rank
                    
                    m_z = folium.Map(location=centroid, zoom_start=15, tiles=None)
                    folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google').add_to(m_z)
                    folium.raster_layers.ImageOverlay(image=cm.get_cmap('RdYlGn')(zonas_map/2.0), bounds=[[miny, minx], [maxy, maxx]], opacity=0.6).add_to(m_z)
                    folium_static(m_z, width=1100, height=700)

            except Exception as e:
                st.error(f"Erro na renderização: {e}")
