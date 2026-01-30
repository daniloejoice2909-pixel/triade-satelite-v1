import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from shapely.geometry import shape, Point
import scipy.ndimage 

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(layout="wide", page_title="Tríade Satélite Pro v2.0")

# Paleta Estilo OneSoil/FieldView
paleta_pro = [
    [0.0, '#a50026'], [0.15, '#d73027'], [0.3, '#f46d43'], 
    [0.5, '#fee08b'], [0.7, '#d9ef8b'], [0.85, '#66bd63'], [1.0, '#1a9850']
]

if "logado" not in st.session_state:
    st.session_state.logado = False
if "lista_imagens" not in st.session_state:
    st.session_state.lista_imagens = []
if "data_selecionada" not in st.session_state:
    st.session_state.data_selecionada = None

# --- 2. LOGIN ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛰️ Tríade Satélite Pro</h1>", unsafe_allow_html=True)
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
    # --- 3. BARRA LATERAL ---
    with st.sidebar:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        st.header("⚙️ Filtros")
        f_geo = st.file_uploader("Contorno (.json)", type=['geojson', 'json'])
        
        st.divider()
        tipo_mapa = st.radio("Camada Técnica:", ["NDVI", "NDRE", "Brilho do Solo", "Imagem Real"])
        
        st.subheader("📅 Período de Busca")
        d_ini = st.date_input("Data Inicial", value=pd.to_datetime("2025-01-01"))
        d_fim = st.date_input("Data Final", value=pd.to_datetime("2025-12-31"))
        
        # BOTÃO QUE VOCÊ PEDIU PARA ACIONAR O COMANDO
        if st.button("🚀 BUSCAR IMAGENS NO PERÍODO", use_container_width=True):
            # Simula a busca no catálogo
            delta = (d_fim - d_ini).days
            st.session_state.lista_imagens = [
                {"data": d_fim.strftime("%d/%m/%Y"), "nuvem": "0%"},
                {"data": (d_ini + pd.Timedelta(days=delta//2)).strftime("%d/%m/%Y"), "nuvem": "12%"},
                {"data": d_ini.strftime("%d/%m/%Y"), "nuvem": "2%"}
            ]
            st.success("Busca concluída! Escolha uma imagem abaixo.")

    # --- 4. ÁREA PRINCIPAL ---
    if f_geo and st.session_state.lista_imagens:
        st.subheader("🖼️ Imagens Encontradas (Selecione a que te agrada)")
        
        cols = st.columns(3)
        for i, img in enumerate(st.session_state.lista_imagens):
            with cols[i]:
                st.info(f"📅 {img['data']}\n\n☁️ Nuvens: {img['nuvem']}")
                if st.button(f"Visualizar Análise: {img['data']}", key=f"sel_{i}"):
                    st.session_state.data_selecionada = img['data']

        if st.session_state.data_selecionada:
            st.divider()
            try:
                # Processamento apenas após a escolha
                geojson_data = json.load(f_geo)
                geom = shape(geojson_data['features'][0]['geometry']) if 'features' in geojson_data else shape(geojson_data)
                minx, miny, maxx, maxy = geom.bounds
                path_coords = list(geom.exterior.coords) if hasattr(geom, 'exterior') else list(geom[0].exterior.coords)

                # Renderização de Alta Fidelidade (OneSoil Style)
                res = 200
                x, y = np.linspace(minx, maxx, res), np.linspace(miny, maxy, res)
                
                # Semente baseada na data para mudar o mapa
                semente = int(pd.to_datetime(st.session_state.data_selecionada, dayfirst=True).timestamp() % 10000)
                np.random.seed(semente)
                
                raw = np.random.uniform(0.3, 0.9, (res, res))
                # Interpolação Bilinear simulada
                matrix = scipy.ndimage.gaussian_filter(raw, sigma=2.0)
                
                for i in range(res):
                    for j in range(res):
                        if not geom.contains(Point(x[j], y[i])):
                            matrix[i, j] = np.nan

                tab1, tab2 = st.tabs(["🛰️ Mapa de Precisão", "🗺️ Zonas de Manejo"])
                
                with tab1:
                    st.subheader(f"{tipo_mapa} - Captura de {st.session_state.data_selecionada}")
                    fig = go.Figure(go.Heatmap(
                        x=x, y=y, z=matrix,
                        colorscale=paleta_pro if "NDVI" in tipo_mapa else "Greens",
                        zsmooth='best',
                        colorbar=dict(title="Índice")
                    ))
                    fig.add_trace(go.Scatter(x=[c[0] for c in path_coords], y=[c[1] for c in path_coords],
                                             mode='lines', line=dict(color='white', width=1.5)))
                    fig.update_yaxes(scaleanchor="x", scaleratio=1)
                    fig.update_layout(height=750, template="plotly_dark")
                    st.plotly_chart(fig, use_container_width=True)

                with tab2:
                    st.subheader("Recomendação em 3 Zonas")
                    valid = matrix[~np.isnan(matrix)].reshape(-1, 1)
                    kmeans = KMeans(n_clusters=3, n_init=10).fit(valid)
                    order = np.argsort(kmeans.cluster_centers_.sum(axis=1))
                    rank = np.zeros_like(kmeans.labels_)
                    for i, o in enumerate(order): rank[kmeans.labels_ == o] = i
                    
                    zonas_map = np.full(matrix.shape, np.nan)
                    zonas_map[~np.isnan(matrix)] = rank

                    fig_z = go.Figure(go.Heatmap(
                        x=x, y=y, z=zonas_map, 
                        colorscale=['#d73027', '#fee08b', '#1a9850'],
                        colorbar=dict(tickvals=[0, 1, 2], ticktext=['Baixa', 'Média', 'Alta'])
                    ))
                    fig_z.update_yaxes(scaleanchor="x", scaleratio=1)
                    fig_z.update_layout(height=750)
                    st.plotly_chart(fig_z, use_container_width=True)

            except Exception as e:
                st.error(f"Erro: {e}")
    else:
        st.info("👋 Danilo, 1º Suba o contorno, 2º Ajuste as datas e 3º Clique no botão 'BUSCAR IMAGENS' na lateral.")
