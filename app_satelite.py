import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from shapely.geometry import shape, Point

# --- CONFIGURAÇÃO ---
st.set_page_config(layout="wide", page_title="Tríade Agro - Monitoramento")

if "logado" not in st.session_state:
    st.session_state.logado = False

# --- TELA DE LOGIN (Simplificada para o exemplo) ---
if not st.session_state.logado:
    # ... (Mantenha seu bloco de login aqui)
    st.session_state.logado = True # Pulando para teste rápido

# --- PLATAFORMA ---
else:
    with st.sidebar:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        st.header("🛰️ Filtro de Satélite")
        f_geo = st.file_uploader("Subir Contorno (.json)", type=['geojson', 'json'])
        
        # Filtro de Datas conforme pedido
        st.date_input("Data Inicial", value=pd.to_datetime("2026-01-01"))
        st.date_input("Data Final", value=pd.to_datetime("2026-01-30"))

    if f_geo:
        geojson_data = json.load(f_geo)
        
        # 1. TRATAMENTO DA GEOMETRIA REAL (Sem achatar)
        if 'features' in geojson_data:
            geom = shape(geojson_data['features'][0]['geometry'])
        else:
            geom = shape(geojson_data)
        
        minx, miny, maxx, maxy = geom.bounds
        path_coords = list(geom.exterior.coords) if hasattr(geom, 'exterior') else list(geom[0].exterior.coords)
        
        # 2. GALERIA DE MINIATURAS (Visualização sem clicar)
        st.subheader("🖼️ Galeria de Imagens Disponíveis")
        col_m1, col_m2, col_m3 = st.columns(3)
        
        datas = [
            {"data": "30/01/2026", "nuvem": "0%", "id": "img1"},
            {"data": "25/01/2026", "nuvem": "5%", "id": "img2"},
            {"data": "15/01/2026", "nuvem": "10%", "id": "img3"}
        ]

        # Lógica de seleção por miniatura
        if "data_ativa" not in st.session_state:
            st.session_state.data_ativa = datas[0]

        for i, d in enumerate([col_m1, col_m2, col_m3]):
            with d:
                # Miniatura visual simulada
                st.write(f"📅 {datas[i]['data']}")
                st.caption(f"☁️ Nuvens: {datas[i]['nuvem']}")
                # Botão que simula a visualização da miniatura
                if st.button(f"Visualizar {datas[i]['data']}", key=datas[i]['id']):
                    st.session_state.data_ativa = datas[i]

        st.divider()

        # 3. MAPA PRINCIPAL COM PROPORÇÃO REAL
        tab1, tab2 = st.tabs(["🌱 NDVI Profissional", "🗺️ Zonas de Manejo (6 Zonas)"])

        # Gerando matriz de dados que respeita o BBOX (contorno)
        res = 100
        x = np.linspace(minx, maxx, res)
        y = np.linspace(miny, maxy, res)
        X, Y = np.meshgrid(x, y)
        
        # Criando máscara para remover o quadriculado de fora
        ndvi_matrix = np.random.uniform(0.4, 0.8, (res, res))
        for i in range(res):
            for j in range(res):
                if not geom.contains(Point(x[j], y[i])):
                    ndvi_matrix[i, j] = np.nan # Deixa transparente fora do contorno

        with tab1:
            st.subheader(f"Análise de Vigor Vegetativo - {st.session_state.data_ativa['data']}")
            fig = go.Figure()
            
            # Heatmap com máscara (NaN fica transparente)
            fig.add_trace(go.Heatmap(
                x=x, y=y, z=ndvi_matrix,
                colorscale='RdYlGn',
                zmin=0.2, zmax=0.9,
                connectgaps=False,
                hoverinfo='none'
            ))
            
            # Linha do Contorno Real
            fig.add_trace(go.Scatter(
                x=[c[0] for c in path_coords],
                y=[c[1] for c in path_coords],
                mode='lines',
                line=dict(color='black', width=2),
                name='Limite Berneck'
            ))

            # Ajuste de escala 1:1 para NÃO ACHATAR
            fig.update_yaxes(scaleanchor="x", scaleratio=1)
            fig.update_layout(height=600, margin=dict(l=0, r=0, b=0, t=40))
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.subheader("Zonas de Manejo Estratégico")
            # Clusterização apenas nos pontos válidos (dentro do talhão)
            valid_data = ndvi_matrix[~np.isnan(ndvi_matrix)].reshape(-1, 1)
            kmeans = KMeans(n_clusters=6, random_state=42).fit(valid_data)
            
            # Remontando o mapa de zonas
            zonas_map = np.full(ndvi_matrix.shape, np.nan)
            zonas_map[~np.isnan(ndvi_matrix)] = kmeans.labels_

            fig_z = go.Figure()
            fig_z.add_trace(go.Heatmap(
                x=x, y=y, z=zonas_map,
                colorscale='RdYlGn'
            ))
            fig_z.update_yaxes(scaleanchor="x", scaleratio=1)
            fig_z.update_layout(height=600)
            st.plotly_chart(fig_z, use_container_width=True)

    else:
        st.info("Aguardando upload do contorno para gerar a galeria de imagens.")
