import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from shapely.geometry import shape, Point

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(layout="wide", page_title="Tríade Agro Estratégica")

# Paleta Profissional NDVI (Padrão FieldView/John Deere)
agri_colors = [
    [0.0, 'rgb(165,0,38)'],   # Vermelho (Crítico)
    [0.2, 'rgb(215,48,39)'],  # Laranja
    [0.4, 'rgb(254,224,139)'],# Amarelo (Transição)
    [0.6, 'rgb(166,217,106)'],# Verde Claro
    [0.8, 'rgb(26,152,80)'],  # Verde
    [1.0, 'rgb(0,68,27)']     # Verde Escuro (Vigor Máximo)
]

if "logado" not in st.session_state:
    st.session_state.logado = False

# --- 2. LOGIN ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛰️ Tríade Satélite v1.0</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        senha = st.text_input("Senha de Acesso", type="password")
        if st.button("ACESSAR"):
            if senha == "triade2026":
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Senha Incorreta")
else:
    # --- 3. DASHBOARD ---
    with st.sidebar:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        st.header("⚙️ Filtros")
        f_geo = st.file_uploader("Upload Contorno (.json)", type=['geojson', 'json'])
        d_ini = st.date_input("Data Inicial", value=pd.to_datetime("2026-01-01"))
        d_fim = st.date_input("Data Final", value=pd.to_datetime("2026-01-30"))

    if f_geo:
        try:
            geojson_data = json.load(f_geo)
            if 'features' in geojson_data:
                geom = shape(geojson_data['features'][0]['geometry'])
            else:
                geom = shape(geojson_data)
            
            minx, miny, maxx, maxy = geom.bounds
            path_coords = list(geom.exterior.coords) if hasattr(geom, 'exterior') else list(geom[0].exterior.coords)
            
            # Galeria de Miniaturas (Visual)
            st.subheader("🖼️ Selecione a Imagem de Satélite")
            cols = st.columns(3)
            datas = ["30/01/2026", "24/01/2026", "18/01/2026"]
            
            if "data_ativa" not in st.session_state:
                st.session_state.data_ativa = datas[0]

            for i, col in enumerate(cols):
                with col:
                    if st.button(f"📅 {datas[i]}\n(SkySat)"):
                        st.session_state.data_ativa = datas[i]

            # GERAÇÃO DO MAPA (Somente se o arquivo existir)
            tab1, tab2 = st.tabs(["🌱 NDVI Profissional", "🗺️ Zonas de Manejo (6 Zonas)"])
            
            # Criando matriz que respeita a proporção real
            res = 120
            x = np.linspace(minx, maxx, res)
            y = np.linspace(miny, maxy, res)
            X, Y = np.meshgrid(x, y)
            ndvi_matrix = np.random.uniform(0.35, 0.88, (res, res)) # Simulação
            
            # Aplicando o recorte (Máscara)
            for i in range(res):
                for j in range(res):
                    if not geom.contains(Point(x[j], y[i])):
                        ndvi_matrix[i, j] = np.nan

            with tab1:
                st.subheader(f"Monitoramento de Vigor - {st.session_state.data_ativa}")
                fig = go.Figure()
                fig.add_trace(go.Heatmap(
                    x=x, y=y, z=ndvi_matrix,
                    colorscale=agri_colors,
                    zmin=np.nanmin(ndvi_matrix), zmax=np.nanmax(ndvi_matrix),
                    connectgaps=False
                ))
                fig.add_trace(go.Scatter(
                    x=[c[0] for c in path_coords], y=[c[1] for c in path_coords],
                    mode='lines', line=dict(color='black', width=2), name='Contorno'
                ))
                fig.update_yaxes(scaleanchor="x", scaleratio=1)
                fig.update_layout(height=700, margin=dict(l=0, r=0, b=0, t=30))
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                st.subheader("Configuração de 6 Zonas Estratégicas")
                valid_data = ndvi_matrix[~np.isnan(ndvi_matrix)].reshape(-1, 1)
                kmeans = KMeans(n_clusters=6, random_state=42).fit(valid_data)
                zonas_map = np.full(ndvi_matrix.shape, np.nan)
                zonas_map[~np.isnan(ndvi_matrix)] = kmeans.labels_

                fig_z = go.Figure()
                fig_z.add_trace(go.Heatmap(x=x, y=y, z=zonas_map, colorscale='RdYlGn'))
                fig_z.update_yaxes(scaleanchor="x", scaleratio=1)
                fig_z.update_layout(height=700)
                st.plotly_chart(fig_z, use_container_width=True)

        except Exception as e:
            st.error(f"Erro ao processar: {e}")
    else:
        st.info("Arraste o arquivo do talhão (.json) na lateral para visualizar as imagens.")
