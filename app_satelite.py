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

# --- 1. CONFIGURAÇÃO DE ALTA FIDELIDADE (Padrão OneSoil/FieldView) ---
st.set_page_config(layout="wide", page_title="Tríade Satélite Pro v3.0")

# Paleta de 7 Níveis - O segredo visual para o cliente
onesoil_colors = ['#d73027', '#f46d43', '#fdae61', '#fee08b', '#d9ef8b', '#66bd63', '#1a9850']
cmap_pro = ListedColormap(onesoil_colors)

if "logado" not in st.session_state:
    st.session_state.logado = False
if "lista_fotos" not in st.session_state:
    st.session_state.lista_fotos = []
if "data_ativa" not in st.session_state:
    st.session_state.data_ativa = None

# --- 2. TELA DE LOGIN ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛰️ Tríade Satélite Pro</h1>", unsafe_allow_True=True)
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
    # --- 3. BARRA LATERAL (CONFIGURAÇÕES) ---
    with st.sidebar:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        st.header("⚙️ Configurações")
        f_geo = st.file_uploader("Contorno do Talhão (.json)", type=['geojson', 'json'])
        
        st.divider()
        tipo_mapa = st.selectbox("Índice de Análise:", 
                                 ["NDVI (Vigor)", "NDRE (Nitrogênio)", "Brilho do Solo", "Imagem Real (Dia)"])
        
        opacidade = st.slider("Transparência da Camada (%)", 0, 100, 70) / 100
        
        st.divider()
        st.subheader("📅 Janela Temporal")
        d_ini = st.date_input("Início", value=pd.to_datetime("2025-01-01"))
        d_fim = st.date_input("Fim", value=pd.to_datetime("2026-01-30"))
        
        if st.button("🚀 BUSCAR IMAGENS", use_container_width=True):
            delta = (d_fim - d_ini).days
            st.session_state.lista_fotos = [
                {"data": d_fim.strftime("%d/%m/%Y"), "nuvem": "0%"},
                {"data": (d_ini + pd.Timedelta(days=delta//2)).strftime("%d/%m/%Y"), "nuvem": "8%"},
                {"data": d_ini.strftime("%d/%m/%Y"), "nuvem": "2%"}
            ]

    # --- 4. FLUXO DE PROCESSAMENTO ---
    if f_geo and st.session_state.lista_fotos:
        st.subheader("🖼️ Galeria de Capturas Disponíveis")
        cols = st.columns(3)
        for i, img in enumerate(st.session_state.lista_fotos):
            with cols[i]:
                st.info(f"📅 {img['data']} | ☁️ {img['nuvem']}")
                if st.button(f"Carregar Captura", key=f"btn_{i}"):
                    st.session_state.data_ativa = img['data']

        if st.session_state.data_ativa:
            try:
                # Carregar Geometria
                geojson_data = json.load(f_geo)
                geom_data = geojson_data['features'][0] if 'features' in geojson_data else geojson_data
                geom = shape(geom_data['geometry'])
                centroid = [geom.centroid.y, geom.centroid.x]
                minx, miny, maxx, maxy = geom.bounds

                # --- MOTOR DE RENDERIZAÇÃO PROFISSIONAL ---
                res = 200 # Alta Definição
                semente = int(pd.to_datetime(st.session_state.data_ativa, dayfirst=True).timestamp() % 10000)
                np.random.seed(semente)
                
                # Simulação de reflectância conforme o índice
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

                # 1. Interpolação Bilinear (Smoothing)
                matrix = scipy.ndimage.gaussian_filter(raw, sigma=sigma)
                
                # 2. Normalização por Contraste Dinâmico (FieldView Style)
                valid_vals = matrix.flatten()
                v_min,
