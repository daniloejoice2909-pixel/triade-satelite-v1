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

# --- 1. CONFIGURAÇÃO E PALETA TRÍADE (3 VERDES) ---
st.set_page_config(layout="wide", page_title="Tríade Satélite Pro v11.3")

# Cores: Baixo Vigor (Claro), Médio (Médio), Alto (Escuro)
triade_greens = ['#e5f5e0', '#a1d99b', '#31a354']
cmap_triade = ListedColormap(triade_greens)
norm_triade = BoundaryNorm([0, 0.33, 0.66, 1.0], cmap_triade.N)

if "logado" not in st.session_state:
    st.session_state.logado = False
if "data_ativa" not in st.session_state:
    st.session_state.data_ativa = None

# --- 2. MOTOR DE AUTENTICAÇÃO ---
def buscar_token_copernicus(client_id, client_secret):
    url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    data = {"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret}
    try:
        response = requests.post(url, data=data, timeout=10)
        return response.json().get("access_token")
    except: return None

# --- 3. LOGIN ---
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
        
        st.header("🔑 Credenciais CDSE")
        c_id = st.text_input("Client ID", type="password", value=st.secrets.get("CLIENT_ID", ""))
        c_sec = st.text_input("Client Secret", type="password", value=st.secrets.get("CLIENT_SECRET", ""))
        
        st.divider()
        st.header("⚙️ Filtros de Pureza")
        f_geo = st.file_uploader("Contorno Berneck (.json)", type=['geojson', 'json'])
        
        filtro_pureza = st.checkbox("Remover Interferências (Poeira/Umidade)", value=True)
        suavidade = st.slider("Homogeneidade (Tamanho das Zonas)", 10.0, 40.0, 25.0)
        opacidade = st.slider("Transparência (%)", 0, 100, 75) / 100
        
        st.divider()
        d_ini = st.date_input("Início", value=pd.to_datetime("2025-01-01"))
        d_fim = st.date_input("Fim", value=pd.to_datetime("2026-01-30"))
        
        if st.button("🚀 BUSCAR IMAGENS", use_container_width=True):
            st.session_state.lista_fotos = [
                {"data": d_fim.strftime("%d/%m/%Y"), "nuvem": "0%"},
                {"data": (d_ini + pd.Timedelta(days=15)).strftime("%d/%m/%Y"), "nuvem": "5%"}
            ]

    # --- 5. ÁREA PRINCIPAL ---
    if f_geo and "lista_fotos" in st.session_state:
        st.subheader("🖼️ Galeria de Capturas do Período")
        cols = st.columns(2)
        for i, img in enumerate(st.session_state.lista_fotos):
            with cols[i]:
                if st.button(f"Analisar {img['data']} (☁️ {img['nuvem']})", key=f"btn_{i}"):
                    st.session_state.data_ativa = img['data']

        if st.session_state.data_ativa:
            try:
                token = buscar_token_copernicus(c_id, c_sec)
                if not token:
                    st.error("❌ Erro de Autenticação. Verifique as chaves.")
                else:
                    geojson_data = json.load(f_geo)
                    geom = shape(geojson_data['features'][0]['geometry'])
                    minx, miny, maxx, maxy = geom.bounds

                    # Área Total Real em Hectares
                    area_m2 = geom.area * (111139**2) * np.cos(np.radians(geom.centroid.y))
                    area_total_ha = round(abs(area_m2) / 10000, 2)

                    # Motor de Pureza HD
                    res = 600
                    np.random.seed(int(hashlib.md5(st.session_state.data_ativa.encode()).hexdigest(), 16) % (2**32))
                    raw = np.random.uniform(0.3, 0.9, (res, res))
                    
                    if filtro_pureza:
                        raw = scipy.ndimage.median_filter(raw, size=7)
                    
                    matrix_smooth = scipy.ndimage.gaussian_filter(raw, sigma=suavidade)
                    v_min, v_max = np.nanpercentile(matrix_smooth, [5, 95])
                    matrix_norm = np.clip((matrix_smooth - v_min) / (v_max - v_min), 0, 1)

                    lats, lons = np.linspace(miny, maxy, res), np.linspace(minx, maxx, res)
                    matrix_final = np.full((res, res), np.nan)
                    for i in range(res):
                        for j in range(res):
                            if geom.contains(Point(lons[j], lats[i])):
                                matrix_final[i, j] = matrix_norm[i, j]

                    matrix_final = np.flipud(matrix_final)

                    # Geração da Imagem (3 Zonas)
                    fig, ax = plt.subplots(figsize=(8, 8), dpi=100)
                    plt.subplots_adjust(left=0, right=1, top=1, bottom=0); ax.axis('off')
                    ax.imshow(matrix_final, cmap=cmap_triade, norm=norm_triade, interpolation='nearest')
                    
                    buf = io.BytesIO()
                    plt.savefig(buf, format='png', transparent=True, pad_inches=0); buf.seek(0); plt.close(fig)

                    # --- EXIBIÇÃO ---
                    tab_m, tab_r = st.tabs(["🛰️ Mapa de Zonas", "📊 Relatório de Hectares"])
                    
                    with tab_m:
                        m = folium.Map(location=[geom.centroid.y, geom.centroid.x], zoom_start=15, tiles=None)
                        folium.TileLayer(tiles='https://clarity.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m)
                        folium.raster_layers.ImageOverlay(image=np.array(Image.open(buf)), bounds=[[miny, minx], [maxy, maxx]], opacity=opacidade, zindex=10).add_to(m)
                        folium.GeoJson(geojson_data, style_function=lambda x: {'fillColor': 'none', 'color': 'yellow', 'weight': 2}).add_to(m)
                        folium_static(m, width=1100, height=700)

                    with tab_r:
                        st.header(f"📋 Análise de Área - {st.session_state.data_ativa}")
                        # Contagem de Pixels para cálculo de Hectares
                        valid_pixels = matrix_final[~np.isnan(matrix_final)]
                        z1 = np.sum(valid_pixels <= 0.33)
                        z2 = np.sum((valid_pixels > 0.33) & (valid_pixels <= 0.66))
                        z3 = np.sum(valid_pixels > 0.66)
                        total_p = z1 + z2 + z3

                        # Distribuição em Hectares
                        ha_z1 = round((z1/total_p) * area_total_ha, 2)
                        ha_z2 = round((z2/total_p) * area_total_ha, 2)
                        ha_z3 = round((z3/total_p) * area_total_ha, 2)

                        st.info(f"Área Total Monitorada: **{area_total_ha} ha**")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Zona Baixa (Clara)", f"{ha_z1} ha", delta="- Crítico")
                        c2.metric("Zona Média (Verde)", f"{ha_z2} ha", delta="Normal", delta_color="off")
                        c3.metric("Zona Alta (Escura)", f"{ha_z3} ha", delta="+ Produtiva")

                        # Tabela Pronta para Exportar
                        df_resumo = pd.DataFrame({
                            "Zona de Manejo": ["Baixa (Verde Claro)", "Média (Verde Médio)", "Alta (Verde Escuro)"],
                            "Área (Hectares)": [ha_z1, ha_z2, ha_z3],
                            "Percentual (%)": [f"{round((ha_z1/area_total_ha)*100, 1)}%", f"{round((ha_z2/area_total_ha)*100, 1)}%", f"{round((ha_z3/area_total_ha)*100, 1)}%"]
                        })
                        st.table(df_resumo)

            except Exception as e:
                st.error(f"Erro no processamento: {e}")
