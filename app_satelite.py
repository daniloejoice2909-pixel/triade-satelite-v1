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
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

# --- 1. CONFIGURAÇÃO DE ALTA FIDELIDADE ---
st.set_page_config(layout="wide", page_title="Tríade Satélite Pro v7.0")

# Paleta OneSoil/FieldView (7 Níveis de Vigor)
fieldview_colors = ['#a50026', '#d73027', '#f46d43', '#fee08b', '#d9ef8b', '#66bd63', '#1a9850']

if "logado" not in st.session_state:
    st.session_state.logado = False
if "lista_fotos" not in st.session_state:
    st.session_state.lista_fotos = []
if "data_ativa" not in st.session_state:
    st.session_state.data_ativa = None

# --- 2. LOGIN TEMATIZADO ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛰️ Tríade Satélite Pro</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        senha = st.text_input("Senha de Acesso Estratégico", type="password")
        if st.button("DESBLOQUEAR PLATAFORMA"):
            if senha == "triade2026":
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Senha Incorreta")
else:
    # --- 3. BARRA LATERAL (CONFIGURAÇÕES COMPLETAS) ---
    with st.sidebar:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        
        st.header("🔑 Credenciais CDSE")
        c_id = st.text_input("Client ID", type="password", value=st.secrets.get("CLIENT_ID", ""))
        c_sec = st.text_input("Client Secret", type="password", value=st.secrets.get("CLIENT_SECRET", ""))
        
        st.divider()
        st.header("⚙️ Configurações")
        f_geo = st.file_uploader("Contorno Berneck (.json)", type=['geojson', 'json'])
        tipo_mapa = st.selectbox("Camada Técnica:", ["NDVI (Vigor)", "NDRE (Nitrogênio)", "Brilho do Solo", "Imagem Real"])
        
        # Controles de Qualidade Visual
        suavidade = st.slider("Homogeneidade (Padrão OneSoil)", 1.0, 5.0, 3.5)
        opacidade = st.slider("Transparência da Camada (%)", 0, 100, 70) / 100
        
        st.divider()
        st.subheader("📅 Período de Busca")
        d_ini = st.date_input("Início", value=pd.to_datetime("2025-01-01"))
        d_fim = st.date_input("Fim", value=pd.to_datetime("2026-01-30"))
        
        if st.button("🚀 BUSCAR IMAGENS NO PERÍODO", use_container_width=True):
            delta = (d_fim - d_ini).days
            st.session_state.lista_fotos = [
                {"data": d_fim.strftime("%d/%m/%Y"), "nuvem": "0%"},
                {"data": (d_ini + pd.Timedelta(days=delta//2)).strftime("%d/%m/%Y"), "nuvem": "8%"},
                {"data": d_ini.strftime("%d/%m/%Y"), "nuvem": "2%"}
            ]

    # --- 4. ÁREA PRINCIPAL ---
    if f_geo and st.session_state.lista_fotos:
        st.subheader("🖼️ Galeria de Capturas (Selecione para processar)")
        cols = st.columns(3)
        for i, img in enumerate(st.session_state.lista_fotos):
            with cols[i]:
                st.info(f"📅 {img['data']} | ☁️ {img['nuvem']}")
                if st.button(f"Carregar {img['data']}", key=f"btn_{i}"):
                    st.session_state.data_ativa = img['data']

        if st.session_state.data_ativa:
            try:
                # 4.1 Processamento de Geometria
                geojson_data = json.load(f_geo)
                geom_data = geojson_data['features'][0] if 'features' in geojson_data else geojson_data
                geom = shape(geom_data['geometry'])
                centroid = [geom.centroid.y, geom.centroid.x]
                minx, miny, maxx, maxy = geom.bounds

                # Cálculo de Área Total (Estimativa em Hectares)
                area_ha = (geom.area * 111139 * 111139 * np.cos(np.radians(geom.centroid.y
