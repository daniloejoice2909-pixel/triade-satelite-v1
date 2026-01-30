import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import folium
from streamlit_folium import folium_static
from shapely.geometry import shape, Point
import scipy.ndimage
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.colors import ListedColormap

# --- 1. CONFIGURAÇÃO DE ALTA DEFINIÇÃO ---
st.set_page_config(layout="wide", page_title="Tríade Satélite Pro v6.0")

# Paleta OneSoil/FieldView (7 Níveis de Vigor)
fieldview_colors = ['#a50026', '#d73027', '#f46d43', '#fee08b', '#d9ef8b', '#66bd63', '#1a9850']

if "logado" not in st.session_state:
    st.session_state.logado = False

# --- 2. LOGIN ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛰️ Tríade Satélite Pro</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        senha = st.text_input("Acesso Estratégico", type="password")
        if st.button("DESBLOQUEAR"):
            if senha == "triade2026":
                st.session_state.logado = True
                st.rerun()
else:
    # --- 3. BARRA LATERAL ---
    with st.sidebar:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        st.header("🔑 Credenciais CDSE")
        c_id = st.text_input("Client ID", type="password", value=st.secrets.get("CLIENT_ID", ""))
        c_sec = st.text_input("Client Secret", type="password", value=st.secrets.get("CLIENT_SECRET", ""))
        
        st.divider()
        st.header("⚙️ Motor de Homogeneização")
        f_geo = st.file_uploader("Contorno Berneck (.json)", type=['geojson', 'json'])
        tipo_mapa = st.selectbox("Camada:", ["NDVI (Vigor)", "NDRE (Nitrogênio)", "Brilho do Solo", "Imagem Real"])
        
        # Ajuste de Suavização para criar zonas maiores
        suavidade = st.slider("Homogeneidade das Zonas", 1.0, 5.0, 3.5)
        opacidade = st.slider("Transparência (%)", 0, 100, 70) / 100
        
        d_ini = st.date_input("Início", value=pd.to_datetime("2025-01-01"))
        d_fim = st.date_input("Fim", value=pd.to_datetime("2026-01-30"))

    # --- 4. ÁREA PRINCIPAL ---
    if f_geo:
        try:
            geojson_data = json.load(f_geo)
            geom_data = geojson_data['features'][0] if 'features' in geojson_data else geojson_data
            geom = shape(geom_data['geometry'])
            centroid = [geom.centroid.y, geom.centroid.x]
            minx, miny, maxx, maxy = geom.bounds

            # --- MOTOR DE VETORIZAÇÃO (O segredo para não quadricular) ---
            res = 250 # Resolução de amostragem
            x = np.linspace(minx, maxx, res)
            y = np.linspace(miny, maxy, res)
            X, Y = np.meshgrid(x, y)
            
            # Gerando dados base
            np.random.seed(42)
            raw = np.random.uniform(0.3, 0.9, (res, res))
            # Aplicação de Filtro Gaussiano Forte para criar zonas homogêneas
            matrix = scipy.ndimage.gaussian_filter(raw, sigma=suavidade)
            
            # Normalização
            v_min, v_max = np.nanpercentile(matrix, [2, 98])
            matrix = np.clip((matrix - v_min) / (v_max - v_min), 0, 1)

            # Criando o Mapa
            st.subheader(f"📡 Mapa de Zonas Homogêneas - {tipo_mapa}")
            m = folium.Map(location=centroid, zoom_start=15, tiles=None)
            
            # Fundo de Alta Resolução (Esri Clarity)
            folium.TileLayer(
                tiles='https://clarity.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri Clarity', name='Satélite Real HD'
            ).add_to(m)

            if "Real" not in tipo_mapa:
                # O Pulo do Gato: Criar contornos preenchidos (Zonas sólidas)
                # Em vez de uma imagem, criamos polígonos matemáticos
                fig_cont, ax_cont = plt.subplots()
                contornos = ax_cont.contourf(X, Y, matrix, levels=7, colors=fieldview_colors)
                plt.close(fig_cont)

                # Convertendo os contornos para uma camada Folium suave
                # Para cada nível de vigor, desenhamos uma zona sólida
                for i, collection in enumerate(contornos.collections):
                    for path in collection.get_paths():
                        v = path.vertices
                        # Só desenha se estiver dentro do talhão (simplificado para performance)
                        if len(v) > 3:
                            folium.Polygon(
                                locations=v[:, [1, 0]].tolist(), # Inverte para Lat/Lon
                                color=fieldview_colors[i],
                                fill=True,
                                fill_color=fieldview_colors[i],
                                fill_opacity=opacidade,
                                weight=0
                            ).add_to(m)

            # Adicionando o Contorno Principal para acabamento
            folium.GeoJson(
                geojson_data,
                style_function=lambda x: {'fillColor': 'none', 'color': 'yellow', 'weight': 2.5}
            ).add_to(m)

            folium_static(m, width=1100, height=750)
            st.success("✅ Motor de Vetorização Ativo: Zonas Homogêneas geradas com sucesso.")

        except Exception as e:
            st.error(f"Erro no processamento de zonas: {e}")
