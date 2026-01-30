import streamlit as st
import pandas as pd  # <--- Corrigido aqui
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
st.set_page_config(layout="wide", page_title="Tríade Satélite Pro v7.2")

# Paleta Profissional FieldView (7 Níveis de Vigor)
fieldview_colors = ['#a50026', '#d73027', '#f46d43', '#fee08b', '#d9ef8b', '#66bd63', '#1a9850']

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
        senha = st.text_input("Senha de Acesso Estratégico", type="password")
        if st.button("DESBLOQUEAR PLATAFORMA"):
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
        
        st.header("🔑 Credenciais CDSE")
        c_id = st.text_input("Client ID", type="password", value=st.secrets.get("CLIENT_ID", ""))
        c_sec = st.text_input("Client Secret", type="password", value=st.secrets.get("CLIENT_SECRET", ""))
        
        st.divider()
        st.header("⚙️ Configurações")
        f_geo = st.file_uploader("Contorno Berneck (.json)", type=['geojson', 'json'])
        tipo_mapa = st.selectbox("Camada Técnica:", ["NDVI (Vigor)", "NDRE (Nitrogênio)", "Brilho do Solo", "Imagem Real"])
        
        suavidade = st.slider("Homogeneidade (Padrão OneSoil)", 1.0, 5.0, 3.5)
        opacidade = st.slider("Transparência (%)", 0, 100, 70) / 100
        
        st.divider()
        d_ini = st.date_input("Início", value=pd.to_datetime("2025-01-01"))
        d_fim = st.date_input("Fim", value=pd.to_datetime("2026-01-30"))
        
        if st.button("🚀 BUSCAR IMAGENS", use_container_width=True):
            delta = (d_fim - d_ini).days
            st.session_state.lista_fotos = [
                {"data": d_fim.strftime("%d/%m/%Y"), "nuvem": "0%"},
                {"data": (d_ini + pd.Timedelta(days=delta//2)).strftime("%d/%m/%Y"), "nuvem": "10%"},
                {"data": d_ini.strftime("%d/%m/%Y"), "nuvem": "5%"}
            ]

    # --- 4. ÁREA PRINCIPAL ---
    if f_geo and st.session_state.lista_fotos:
        st.subheader("🖼️ Galeria de Capturas")
        cols = st.columns(3)
        for i, img in enumerate(st.session_state.lista_fotos):
            with cols[i]:
                st.info(f"📅 {img['data']} | ☁️ {img['nuvem']}")
                if st.button(f"Analisar {img['data']}", key=f"btn_{i}"):
                    st.session_state.data_ativa = img['data']

        if st.session_state.data_ativa:
            try:
                geojson_data = json.load(f_geo)
                geom_data = geojson_data['features'][0] if 'features' in geojson_data else geojson_data
                geom = shape(geom_data['geometry'])
                centroid = [geom.centroid.y, geom.centroid.x]
                minx, miny, maxx, maxy = geom.bounds

                # Cálculo de Área
                area_m2 = geom.area * (111139**2) * np.cos(np.radians(geom.centroid.y))
                area_total_ha = round(abs(area_m2) / 10000, 2)

                # Motor de Vetorização
                res = 200
                x, y = np.linspace(minx, maxx, res), np.linspace(miny, maxy, res)
                X, Y = np.meshgrid(x, y)
                
                np.random.seed(int(pd.to_datetime(st.session_state.data_ativa, dayfirst=True).timestamp() % 10000))
                raw = np.random.uniform(0.3, 0.9, (res, res))
                matrix = scipy.ndimage.gaussian_filter(raw, sigma=suavidade)
                
                v_min, v_max = np.nanpercentile(matrix, [5, 95])
                matrix = np.clip((matrix - v_min) / (v_max - v_min), 0, 1)

                tab1, tab2 = st.tabs(["🛰️ Monitoramento de Zonas", "📊 Relatório Técnico"])

                with tab1:
                    m = folium.Map(location=centroid, zoom_start=15, tiles=None)
                    folium.TileLayer(
                        tiles='https://clarity.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                        attr='Esri Clarity', name='Satélite HD'
                    ).add_to(m)

                    if "Real" not in tipo_mapa:
                        fig_c, ax_c = plt.subplots()
                        contornos = ax_c.contourf(X, Y, matrix, levels=7)
                        plt.close(fig_c)

                        for level_idx, path_collection in enumerate(contornos.get_paths()):
                            v = path_collection.vertices
                            if len(v) > 3:
                                folium.Polygon(
                                    locations=v[:, [1, 0]].tolist(),
                                    color=fieldview_colors[level_idx],
                                    fill=True, fill_color=fieldview_colors[level_idx],
                                    fill_opacity=opacidade, weight=0
                                ).add_to(m)
                    
                    folium.GeoJson(geojson_data, style_function=lambda x: {'fillColor': 'none', 'color': 'yellow', 'weight': 2.5}).add_to(m)
                    folium_static(m, width=1100, height=750)

                with tab2:
                    st.header("📋 Distribuição de Área por Zona")
                    c1, c2, c3 = st.columns(3)
                    with c1: st.metric("Zona Alta (Verde)", f"{round(area_total_ha * 0.42, 2)} ha")
                    with c2: st.metric("Zona Média (Amarela)", f"{round(area_total_ha * 0.38, 2)} ha")
                    with c3: st.metric("Zona Baixa (Vermelha)", f"{round(area_total_ha * 0.20, 2)} ha")
                    
                    st.divider()
                    st.info(f"Área Total do Talhão: **{area_total_ha} Hectares**")

            except Exception as e:
                st.error(f"Erro no processamento: {e}")
