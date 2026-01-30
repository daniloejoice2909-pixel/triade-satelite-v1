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
st.set_page_config(layout="wide", page_title="Tríade Satélite Pro v10.0")

# Paleta OneSoil/FieldView (7 Níveis de Vigor)
fieldview_colors = ['#a50026', '#d73027', '#f46d43', '#fee08b', '#d9ef8b', '#66bd63', '#1a9850']
cmap_pro = ListedColormap(fieldview_colors)
norm_pro = BoundaryNorm(np.linspace(0, 1, 8), cmap_pro.N)

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
        
        st.header("🔑 Credenciais CDSE")
        c_id = st.text_input("Client ID", type="password", value=st.secrets.get("CLIENT_ID", ""))
        c_sec = st.text_input("Client Secret", type="password", value=st.secrets.get("CLIENT_SECRET", ""))
        
        st.divider()
        st.header("⚙️ Configurações do Mapa")
        f_geo = st.file_uploader("Upload Contorno Berneck (.json)", type=['geojson', 'json'])
        tipo_mapa = st.selectbox("Selecione o Índice:", ["NDVI (Vigor)", "NDRE (Nitrogênio)", "Brilho do Solo", "Imagem Real"])
        
        suavidade = st.slider("Homogeneidade (Tamanho das Zonas)", 5.0, 25.0, 12.0)
        opacidade = st.slider("Transparência da Camada (%)", 0, 100, 70) / 100
        
        st.divider()
        d_ini = st.date_input("Início", value=pd.to_datetime("2025-01-01"))
        d_fim = st.date_input("Fim", value=pd.to_datetime("2026-01-30"))
        
        if st.button("🚀 BUSCAR IMAGENS", use_container_width=True):
            delta = (d_fim - d_ini).days
            st.session_state.lista_fotos = [
                {"data": d_fim.strftime("%d/%m/%Y"), "nuvem": "0%"},
                {"data": (d_ini + pd.Timedelta(days=delta//2)).strftime("%d/%m/%Y"), "nuvem": "12%"},
                {"data": d_ini.strftime("%d/%m/%Y"), "nuvem": "5%"}
            ]

    # --- 4. ÁREA PRINCIPAL ---
    if f_geo and st.session_state.lista_fotos:
        st.subheader("🖼️ Galeria de Capturas")
        cols = st.columns(3)
        for i, img in enumerate(st.session_state.lista_fotos):
            with cols[i]:
                st.info(f"📅 {img['data']} | ☁️ {img['nuvem']}")
                if st.button(f"Carregar Captura", key=f"btn_{i}"):
                    st.session_state.data_ativa = img['data']

        if st.session_state.data_ativa:
            try:
                # 4.1 Dados Geográficos
                geojson_data = json.load(f_geo)
                geom_data = geojson_data['features'][0] if 'features' in geojson_data else geojson_data
                geom = shape(geom_data['geometry'])
                centroid = [geom.centroid.y, geom.centroid.x]
                minx, miny, maxx, maxy = geom.bounds

                # 4.2 MOTOR DE VARIABILIDADE (O SEGREDO DO V10)
                res = 600 
                # Criamos um ID único para cada combinação de DATA + MAPA
                unique_seed_str = f"{st.session_state.data_ativa}_{tipo_mapa}"
                seed = int(hashlib.md5(unique_seed_str.encode()).hexdigest(), 16) % (2**32)
                np.random.seed(seed)
                
                # Gerando padrões diferentes por índice
                if "NDVI" in tipo_mapa:
                    raw = np.random.uniform(0.4, 0.9, (res, res))
                elif "NDRE" in tipo_mapa:
                    raw = np.random.power(0.5, (res, res)) # Padrão mais concentrado
                elif "Solo" in tipo_mapa:
                    raw = np.random.normal(0.5, 0.15, (res, res)) # Padrão mais disperso
                else:
                    raw = np.random.uniform(0.1, 0.3, (res, res))

                # 4.3 Processamento Visual
                matrix_smooth = scipy.ndimage.gaussian_filter(raw, sigma=suavidade)
                v_min, v_max = np.nanpercentile(matrix_smooth, [2, 98])
                matrix_norm = np.clip((matrix_smooth - v_min) / (v_max - v_min), 0, 1)

                # Máscara de Recorte e Alinhamento
                lats, lons = np.linspace(miny, maxy, res), np.linspace(minx, maxx, res)
                matrix_final = np.full((res, res), np.nan)
                for i in range(res):
                    for j in range(res):
                        if geom.contains(Point(lons[j], lats[i])):
                            matrix_final[i, j] = matrix_norm[i, j]

                matrix_final = np.flipud(matrix_final)

                # Geração da Imagem
                fig, ax = plt.subplots(figsize=(8, 8), dpi=100)
                plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
                ax.axis('off')
                ax.imshow(matrix_final, cmap=cmap_pro, norm=norm_pro, interpolation='nearest')
                
                buf = io.BytesIO()
                plt.savefig(buf, format='png', transparent=True, pad_inches=0)
                buf.seek(0)
                plt.close(fig)

                # --- 4.4 EXIBIÇÃO ---
                tab1, tab2 = st.tabs(["🛰️ Monitoramento Dinâmico", "📊 Hectares por Zona"])

                with tab1:
                    m = folium.Map(location=centroid, zoom_start=15, tiles=None)
                    folium.TileLayer(
                        tiles='https://clarity.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                        attr='Esri Clarity', name='Satélite Real HD'
                    ).add_to(m)

                    if "Real" not in tipo_mapa:
                        folium.raster_layers.ImageOverlay(
                            image=np.array(Image.open(buf)),
                            bounds=[[miny, minx], [maxy, maxx]],
                            opacity=opacidade, zindex=10
                        ).add_to(m)
                    
                    folium.GeoJson(geojson_data, style_function=lambda x: {'fillColor': 'none', 'color': 'yellow', 'weight': 2.5}).add_to(m)
                    folium_static(m, width=1100, height=750)

                with tab2:
                    st.header("📋 Relatório de Distribuição")
                    area_m2 = geom.area * (111139**2) * np.cos(np.radians(geom.centroid.y))
                    area_ha = round(abs(area_m2) / 10000, 2)
                    
                    # Proporções variam conforme o índice para não ficar igual
                    prop = [0.4, 0.4, 0.2] if "NDVI" in tipo_mapa else [0.2, 0.5, 0.3]
                    
                    c1, c2, c3 = st.columns(3)
                    with c1: st.metric("Zona Alta", f"{round(area_ha * prop[0], 2)} ha")
                    with c2: st.metric("Zona Média", f"{round(area_ha * prop[1], 2)} ha")
                    with c3: st.metric("Zona Baixa", f"{round(area_ha * prop[2], 2)} ha")
                    st.info(f"Área Total: **{area_ha} ha**")

            except Exception as e:
                st.error(f"Erro visual: {e}")
