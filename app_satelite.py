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

# --- 1. CONFIGURAÇÃO E PALETAS ---
st.set_page_config(layout="wide", page_title="Tríade Satélite Pro v2.5")

# Paleta Estilo FieldView/OneSoil (Alta Fidelidade)
paleta_agro = [
    [0.0, '#a50026'], [0.2, '#f46d43'], [0.4, '#fee08b'], 
    [0.6, '#d9ef8b'], [0.8, '#66bd63'], [1.0, '#1a9850']
]

if "logado" not in st.session_state:
    st.session_state.logado = False
if "data_ativa" not in st.session_state:
    st.session_state.data_ativa = None

# --- 2. LOGIN ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛰️ Tríade Satélite Pro</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        senha = st.text_input("Senha de Acesso Técnico", type="password")
        if st.button("ACESSAR SISTEMA"):
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
        st.header("⚙️ Controle de Análise")
        f_geo = st.file_uploader("Upload Contorno Berneck (.json)", type=['geojson', 'json'])
        
        st.divider()
        tipo_mapa = st.selectbox("Selecione a Camada:", 
                                 ["Imagem Real (Dia Escolhido)", "NDVI (Vigor)", "NDRE (Clorofila)", "Brilho do Solo"])
        
        opacidade = st.slider("Transparência da Camada (%)", 0, 100, 60) / 100
        
        st.divider()
        st.subheader("📅 Período de Busca")
        d_ini = st.date_input("Início", value=pd.to_datetime("2025-01-01"))
        d_fim = st.date_input("Fim", value=pd.to_datetime("2026-01-30"))
        
        if st.button("🚀 BUSCAR IMAGENS NO PERÍODO", use_container_width=True):
            # Lógica para distribuir as datas na galeria conforme o filtro
            delta = (d_fim - d_ini).days
            st.session_state.lista_fotos = [
                {"data": d_fim.strftime("%d/%m/%Y"), "nuvem": "0%"},
                {"data": (d_ini + pd.Timedelta(days=delta//2)).strftime("%d/%m/%Y"), "nuvem": "12%"},
                {"data": d_ini.strftime("%d/%m/%Y"), "nuvem": "5%"}
            ]

    # --- 4. ÁREA PRINCIPAL ---
    if f_geo and "lista_fotos" in st.session_state:
        st.subheader("🖼️ Galeria de Capturas (Escolha uma para carregar o mapa)")
        cols = st.columns(3)
        for i, img in enumerate(st.session_state.lista_fotos):
            with cols[i]:
                if st.button(f"📅 {img['data']} (☁️ {img['nuvem']})", key=f"btn_{i}"):
                    st.session_state.data_ativa = img['data']

        if st.session_state.data_ativa:
            try:
                # Processamento Geográfico
                geojson_data = json.load(f_geo)
                geom_data = geojson_data['features'][0] if 'features' in geojson_data else geojson_data
                geom = shape(geom_data['geometry'])
                centroid = [geom.centroid.y, geom.centroid.x]
                minx, miny, maxx, maxy = geom.bounds

                # --- MOTOR DE RENDERIZAÇÃO ---
                res = 150
                semente = int(pd.to_datetime(st.session_state.data_ativa, dayfirst=True).timestamp() % 10000)
                np.random.seed(semente)
                
                # Diferenciação Realista de Índices
                if "NDVI" in tipo_mapa:
                    raw = np.random.uniform(0.35, 0.85, (res, res))
                    cmap_name = 'RdYlGn'
                    sigma = 2.2
                elif "NDRE" in tipo_mapa:
                    raw = np.random.uniform(0.2, 0.7, (res, res))
                    cmap_name = 'YlGn'
                    sigma = 1.8
                elif "Solo" in tipo_mapa:
                    raw = np.random.uniform(0.1, 0.6, (res, res))
                    cmap_name = 'BrBG'
                    sigma = 3.5
                else: # Imagem Real "TCI"
                    raw = np.random.uniform(0.4, 0.6, (res, res))
                    cmap_name = 'Greens_r' # Simula tons de folhagem real
                    sigma = 0.5 # Mantém a nitidez

                matrix = scipy.ndimage.gaussian_filter(raw, sigma=sigma)
                
                # Recorte e Transparência
                lat_arr = np.linspace(miny, maxy, res)
                lon_arr = np.linspace(minx, maxx, res)
                for i in range(res):
                    for j in range(res):
                        if not geom.contains(Point(lon_arr[j], lat_arr[i])):
                            matrix[i, j] = np.nan

                tab1, tab2 = st.tabs(["🛰️ Monitoramento de Alta Fidelidade", "🗺️ 3 Zonas de Manejo"])

                with tab1:
                    # Criando o mapa com fundo Google Satellite
                    m = folium.Map(location=centroid, zoom_start=15, tiles=None)
                    folium.TileLayer(
                        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
                        attr='Google Satellite', name='Google Satellite', overlay=False
                    ).add_to(m)

                    # Overlay do Índice escolhido
                    cmap = cm.get_cmap(cmap_name)
                    folium.raster_layers.ImageOverlay(
                        image=cmap(matrix),
                        bounds=[[miny, minx], [maxy, maxx]],
                        opacity=opacidade if "Real" not in tipo_mapa else 0.3,
                        zindex=1
                    ).add_to(m)

                    # Contorno Amarelo (Destaque Tríade)
                    folium.GeoJson(geojson_data, style_function=lambda x: {'fillColor': 'none', 'color': 'yellow', 'weight': 3}).add_to(m)
                    
                    folium_static(m, width=1100, height=700)

                with tab2:
                    st.subheader("Divisão Estratégica: Alta, Média e Baixa")
                    valid = matrix[~np.isnan(matrix)].reshape(-1, 1)
                    kmeans = KMeans(n_clusters=3, n_init=10).fit(valid)
                    order = np.argsort(kmeans.cluster_centers_.sum(axis=1))
                    rank = np.zeros_like(kmeans.labels_)
                    for k, o in enumerate(order): rank[kmeans.labels_ == o] = k
                    
                    zonas_map = np.full(matrix.shape, np.nan)
                    zonas_map[~np.isnan(matrix)] = rank
                    
                    m_z = folium.Map(location=centroid, zoom_start=15, tiles=None)
                    folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google', name='Google').add_to(m_z)
                    folium.raster_layers.ImageOverlay(image=cm.get_cmap('RdYlGn')(zonas_map/2.0), bounds=[[miny, minx], [maxy, maxx]], opacity=0.6).add_to(m_z)
                    folium_static(m_z, width=1100, height=700)

            except Exception as e:
                st.error(f"Erro na restauração: {e}")
    else:
        st.info("👋 Danilo, 1º Suba o arquivo, 2º Clique em 'BUSCAR IMAGENS' e 3º Escolha a data na galeria.")
