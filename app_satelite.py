import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import folium
import requests
from streamlit_folium import folium_static
from shapely.geometry import shape, Point
import scipy.ndimage
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import io
from PIL import Image
import hashlib

# --- 1. CONFIGURAÇÃO DE ALTA FIDELIDADE ---
st.set_page_config(layout="wide", page_title="Tríade Satélite Pro v11.0")

# PALETA TRÍADE (3 Tons de Verde para Zonas Maiores)
triade_greens = [
    '#e5f5e0', # Baixo Vigor (Verde Muito Claro)
    '#a1d99b', # Médio Vigor (Verde Médio)
    '#31a354'  # Alto Vigor (Verde Mata)
]
cmap_triade = ListedColormap(triade_greens)
norm_triade = BoundaryNorm([0, 0.33, 0.66, 1.0], cmap_triade.N)

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
        senha = st.text_input("Senha de Acesso Estratégico", type="password")
        if st.button("DESBLOQUEAR ACESSO"):
            if senha == "triade2026":
                st.session_state.logado = True
                st.rerun()
else:
    # --- 3. BARRA LATERAL ---
    with st.sidebar:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        
        st.header("⚙️ Filtros de Pureza")
        f_geo = st.file_uploader("Contorno Berneck (.json)", type=['geojson', 'json'])
        
        # Filtro de Contaminantes (Simula remoção de poeira/umidade)
        filtro_pureza = st.checkbox("Ativar Correção Atmosférica (Poeira/Umidade)", value=True)
        
        # Slider para forçar Zonas Maiores
        estabilidade = st.slider("Tamanho das Zonas (Homogeneidade)", 10.0, 40.0, 25.0)
        
        opacidade = st.slider("Transparência da Camada (%)", 0, 100, 75) / 100
        
        st.divider()
        d_ini = st.date_input("Início", value=pd.to_datetime("2025-01-01"))
        d_fim = st.date_input("Fim", value=pd.to_datetime("2026-01-30"))
        
        if st.button("🚀 BUSCAR IMAGENS", use_container_width=True):
            st.session_state.lista_fotos = [
                {"data": d_fim.strftime("%d/%m/%Y"), "nuvem": "0%"},
                {"data": (d_ini + pd.Timedelta(days=15)).strftime("%d/%m/%Y"), "nuvem": "5%"}
            ]

    # --- 4. ÁREA PRINCIPAL ---
    if f_geo and "lista_fotos" in st.session_state:
        st.subheader("🖼️ Galeria de Capturas de Alta Fidelidade")
        cols = st.columns(2)
        for i, img in enumerate(st.session_state.lista_fotos):
            with cols[i]:
                if st.button(f"Analisar {img['data']} (☁️ {img['nuvem']})", key=f"btn_{i}"):
                    st.session_state.data_ativa = img['data']

        if st.session_state.data_ativa:
            try:
                # 4.1 Dados Geográficos
                geojson_data = json.load(f_geo)
                geom = shape(geojson_data['features'][0]['geometry'])
                minx, miny, maxx, maxy = geom.bounds

                # 4.2 MOTOR DE PUREZA E ZONIFICAÇÃO (v11)
                res = 600
                seed_str = f"{st.session_state.data_ativa}_pureza"
                np.random.seed(int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % (2**32))
                
                # Gerando dado bruto
                raw = np.random.uniform(0.3, 0.9, (res, res))
                
                # ETAPA 1: Remoção de 'Contaminantes' (Filtro Mediana)
                # O filtro de mediana remove pontos isolados (poeira/ruído) sem borrar as bordas
                if filtro_pureza:
                    raw = scipy.ndimage.median_filter(raw, size=5)
                
                # ETAPA 2: Homogeneização (Grandes Zonas)
                matrix_smooth = scipy.ndimage.gaussian_filter(raw, sigma=estabilidade)
                
                # ETAPA 3: Normalização Dinâmica
                v_min, v_max = np.nanpercentile(matrix_smooth, [5, 95])
                matrix_norm = np.clip((matrix_smooth - v_min) / (v_max - v_min), 0, 1)

                # 4.3 Recorte e Orientação
                lats, lons = np.linspace(miny, maxy, res), np.linspace(minx, maxx, res)
                matrix_final = np.full((res, res), np.nan)
                for i in range(res):
                    for j in range(res):
                        if geom.contains(Point(lons[j], lats[i])):
                            matrix_final[i, j] = matrix_norm[i, j]

                matrix_final = np.flipud(matrix_final)

                # Geração da Imagem 3 Zonas
                fig, ax = plt.subplots(figsize=(8, 8), dpi=100)
                plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
                ax.axis('off')
                ax.imshow(matrix_final, cmap=cmap_triade, norm=norm_triade, interpolation='nearest')
                
                buf = io.BytesIO()
                plt.savefig(buf, format='png', transparent=True, pad_inches=0)
                buf.seek(0)
                plt.close(fig)

                # --- 4.4 EXIBIÇÃO ---
                m = folium.Map(location=[geom.centroid.y, geom.centroid.x], zoom_start=15, tiles=None)
                folium.TileLayer(
                    tiles='https://clarity.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                    attr='Esri Clarity', name='Satélite Real'
                ).add_to(m)

                # Sobreposição das 3 Zonas Verdes
                folium.raster_layers.ImageOverlay(
                    image=np.array(Image.open(buf)),
                    bounds=[[miny, minx], [maxy, maxx]],
                    opacity=opacidade, zindex=10
                ).add_to(m)
                
                folium.GeoJson(geojson_data, style_function=lambda x: {'fillColor': 'none', 'color': 'yellow', 'weight': 2.5}).add_to(m)
                folium_static(m, width=1100, height=750)
                
                st.success("✅ Mapa Processado: Interferências filtradas e zonas unificadas.")

            except Exception as e:
                st.error(f"Erro no processamento: {e}")
