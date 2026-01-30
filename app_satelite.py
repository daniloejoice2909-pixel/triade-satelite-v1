import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import folium
import requests
from streamlit_folium import folium_static
from sklearn.cluster import KMeans
from shapely.geometry import shape, Point
import scipy.ndimage
import matplotlib.cm as cm
from matplotlib.colors import ListedColormap

# --- 1. CONFIGURAÇÃO DE ALTA DEFINIÇÃO (Padrão OneSoil/FieldView) ---
st.set_page_config(layout="wide", page_title="Tríade Satélite Pro v4.1")

# Paleta FieldView de 7 Níveis (Cores Vivas e Definidas)
onesoil_colors = ['#a50026', '#d73027', '#f46d43', '#fee08b', '#d9ef8b', '#66bd63', '#1a9850']
cmap_pro = ListedColormap(onesoil_colors)

# --- 2. MOTOR DE PROCESSAMENTO HD ---
def processar_imagem_hd(raw_data, res, sigma_val):
    """
    Transforma dados brutos em mapas nítidos com padrão de mercado.
    """
    # 1. Interpolação Bilinear Controlada (Evita o borrão excessivo)
    matrix = scipy.ndimage.gaussian_filter(raw_data, sigma=sigma_val)
    
    # 2. Normalização de Contraste Local (O segredo da nitidez)
    # Ignoramos os 2% extremos para evitar que um brilho de nuvem 'lave' o mapa
    valid_vals = matrix[~np.isnan(matrix)]
    if valid_vals.size > 0:
        v_min, v_max = np.nanpercentile(valid_vals, [2, 98])
        matrix = np.clip((matrix - v_min) / (v_max - v_min), 0, 1)
    
    return matrix

# --- 3. LOGIN (Restauração da Proteção) ---
if "logado" not in st.session_state:
    st.session_state.logado = False

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
    # --- 4. BARRA LATERAL ---
    with st.sidebar:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        st.header("⚙️ Controle de Precisão")
        f_geo = st.file_uploader("Upload Contorno (.json)", type=['geojson', 'json'])
        
        st.divider()
        tipo_mapa = st.selectbox("Índice de Análise:", ["NDVI (Vigor)", "NDRE (Nitrogênio)", "Imagem Real"])
        
        # SLIDER DE NITIDEZ: Para você ajustar conforme o tamanho do talhão
        nitidez = st.slider("Ajuste de Nitidez (Menos é mais nítido)", 0.5, 5.0, 1.5)
        opacidade = st.slider("Transparência da Camada (%)", 0, 100, 75) / 100
        
        st.divider()
        if st.button("🚀 PROCESSAR COM ALTA FIDELIDADE", use_container_width=True):
            st.session_state.processar = True

    # --- 5. EXECUÇÃO DO MAPA HD ---
    if f_geo and st.session_state.get('processar'):
        try:
            geojson_data = json.load(f_geo)
            geom = shape(geojson_data['features'][0]['geometry'])
            minx, miny, maxx, maxy = geom.bounds
            centroid = [geom.centroid.y, geom.centroid.x]

            # RESOLUÇÃO HD: 350x350 pixels (Mais denso que o OneSoil padrão)
            res = 350 
            semente = 42 # Fixo para teste de nitidez
            np.random.seed(semente)
            
            # Simulando o dado do Sentinel-2 (Refletância Real)
            raw = np.random.uniform(0.3, 0.9, (res, res))
            
            # APLICAÇÃO DO MOTOR HD
            matrix = processar_imagem_hd(raw, res, nitidez)
            
            # Correção de Orientação e Recorte
            matrix = np.flipud(matrix)
            lats = np.linspace(miny, maxy, res)
            lons = np.linspace(minx, maxx, res)
            for i in range(res):
                for j in range(res):
                    if not geom.contains(Point(lons[j], lats[res-1-i])):
                        matrix[i, j] = np.nan

            # --- RENDERIZAÇÃO ---
            st.subheader(f"Análise Técnica HD - Talhão Berneck")
            m = folium.Map(location=centroid, zoom_start=15, tiles=None)
            
            # Fundo Google Satellite (Realidade)
            folium.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
                attr='Google', name='Google Satellite', overlay=False
            ).add_to(m)

            # Camada Técnica Discretizada (Sem borrão)
            color_data = cmap_pro(matrix)
            folium.raster_layers.ImageOverlay(
                image=color_data,
                bounds=[[miny, minx], [maxy, maxx]],
                opacity=opacidade
            ).add_to(m)

            folium.GeoJson(geojson_data, style_function=lambda x: {'fillColor': 'none', 'color': 'yellow', 'weight': 2}).add_to(m)
            folium_static(m, width=1100, height=750)

        except Exception as e:
            st.error(f"Erro na renderização HD: {e}")
