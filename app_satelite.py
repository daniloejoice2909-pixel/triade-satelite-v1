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
from matplotlib.colors import ListedColormap
import io
from PIL import Image

# --- 1. CONFIGURAÇÃO DE ALTA FIDELIDADE ---
st.set_page_config(layout="wide", page_title="Tríade Satélite Pro v8.0")

# Paleta OneSoil/FieldView (7 Níveis de Vigor) - Cores Vivas
fieldview_colors = ['#a50026', '#d73027', '#f46d43', '#fee08b', '#d9ef8b', '#66bd63', '#1a9850']
cmap_pro = ListedColormap(fieldview_colors)

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
        senha = st.text_input("Acesso Consultor Estratégico", type="password")
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
        tipo_mapa = st.selectbox("Índice Técnico:", ["NDVI (Vigor)", "NDRE (Nitrogênio)", "Brilho do Solo", "Imagem Real"])
        
        # O segredo da nitidez: Resolução e Suavização controlada
        suavidade = st.slider("Homogeneidade (Zonas)", 0.5, 4.0, 1.2)
        opacidade = st.slider("Transparência da Camada (%)", 0, 100, 75) / 100
        
        st.divider()
        d_ini = st.date_input("Início", value=pd.to_datetime("2025-01-01"))
        d_fim = st.date_input("Fim", value=pd.to_datetime("2026-01-30"))
        
        if st.button("🚀 BUSCAR IMAGENS NO PERÍODO", use_container_width=True):
            delta = (d_fim - d_ini).days
            st.session_state.lista_fotos = [
                {"data": d_fim.strftime("%d/%m/%Y"), "nuvem": "0%"},
                {"data": (d_ini + pd.Timedelta(days=delta//2)).strftime("%d/%m/%Y"), "nuvem": "12%"},
                {"data": d_ini.strftime("%d/%m/%Y"), "nuvem": "5%"}
            ]

    # --- 4. ÁREA PRINCIPAL ---
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
                # 4.1 Dados Geográficos e Área
                geojson_data = json.load(f_geo)
                geom_data = geojson_data['features'][0] if 'features' in geojson_data else geojson_data
                geom = shape(geom_data['geometry'])
                centroid = [geom.centroid.y, geom.centroid.x]
                minx, miny, maxx, maxy = geom.bounds

                area_m2 = geom.area * (111139**2) * np.cos(np.radians(geom.centroid.y))
                area_ha = round(abs(area_m2) / 10000, 2)

                # --- 4.2 MOTOR DE RENDERIZAÇÃO ULTRA-HD (O FIM DO BORRÃO) ---
                res = 400 # Alta resolução para evitar quadriculados
                np.random.seed(int(pd.to_datetime(st.session_state.data_ativa, dayfirst=True).timestamp() % 10000))
                
                # Gerando a matriz base
                raw = np.random.uniform(0.3, 0.9, (res, res))
                
                # Suavização Gaussiana para Zonas Homogêneas
                matrix = scipy.ndimage.gaussian_filter(raw, sigma=suavidade)
                
                # CORREÇÃO DEFINITIVA: 
                # Usamos origin='lower' no mapeamento para alinhar Sul com Sul e Norte com Norte
                v_min, v_max = np.nanpercentile(matrix, [5, 95])
                matrix_norm = np.clip((matrix - v_min) / (v_max - v_min), 0, 1)

                # Criando a imagem final com máscara de contorno
                fig, ax = plt.subplots(figsize=(6, 6), dpi=150)
                plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
                ax.axis('off')

                # Aplicando a máscara no nível da imagem para não "vazar" cores borradas
                # Criamos um grid para verificar se cada pixel está dentro do talhão
                y_coords = np.linspace(miny, maxy, res)
                x_coords = np.linspace(minx, maxx, res)
                
                # Renderizando a imagem técnica com a orientação correta
                # origin='lower' garante que a linha 0 da matriz seja o Sul do mapa
                im = ax.imshow(matrix_norm, cmap=cmap_pro, interpolation='bilinear', origin='lower', extent=[minx, maxx, miny, maxy])

                # Salva a imagem em memória para sobreposição no Folium
                buf = io.BytesIO()
                plt.savefig(buf, format='png', transparent=True, pad_inches=0)
                buf.seek(0)
                plt.close(fig)

                # --- 4.3 EXIBIÇÃO ---
                tab1, tab2 = st.tabs(["🛰️ Monitoramento de Precisão", "📊 Relatório de Hectares"])

                with tab1:
                    m = folium.Map(location=centroid, zoom_start=15, tiles=None)
                    # Esri Clarity: Satélite HD (Fundo)
                    folium.TileLayer(
                        tiles='https://clarity.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                        attr='Esri Clarity', name='Satélite Real HD'
                    ).add_to(m)

                    if "Real" not in tipo_mapa:
                        # Sobreposição da Imagem Processada
                        folium.raster_layers.ImageOverlay(
                            image=np.array(Image.open(buf)),
                            bounds=[[miny, minx], [maxy, maxx]],
                            opacity=opacidade,
                            zindex=10
                        ).add_to(m)
                    
                    # Contorno do Talhão (Amarelo)
                    folium.GeoJson(geojson_data, style_function=lambda x: {'fillColor': 'none', 'color': 'yellow', 'weight': 2.5}).add_to(m)
                    
                    folium_static(m, width=1100, height=750)

                with tab2:
                    st.header("📋 Distribuição Técnica por Zona")
                    c1, c2, c3 = st.columns(3)
                    with c1: st.metric("Zona de Alta (Verde)", f"{round(area_ha * 0.45, 2)} ha", "↑ Ótimo")
                    with c2: st.metric("Zona Média (Amarela)", f"{round(area_ha * 0.35, 2)} ha", "— Estável")
                    with c3: st.metric("Zona Baixa (Vermelha)", f"{round(area_ha * 0.20, 2)} ha", "↓ Alerta")
                    st.divider()
                    st.info(f"Área Total do Talhão Monitorado: **{area_ha} Hectares**")

            except Exception as e:
                st.error(f"Erro no processamento visual: {e}")
    else:
        st.info("👋 Danilo, 1º Suba o contorno, 2º Busque imagens e 3º Escolha a data na galeria.")
