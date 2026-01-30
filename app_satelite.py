import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import requests
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from shapely.geometry import shape, Point
import scipy.ndimage 

# --- 1. CONFIGURAÇÃO INICIAL ---
st.set_page_config(layout="wide", page_title="Tríade Agro Estratégica")

# Paleta Profissional Vibrante para NDVI
agri_vibrante = [
    [0.0, 'rgb(215,48,39)'],   # Vermelho (Estresse)
    [0.2, 'rgb(252,141,89)'],  # Laranja
    [0.4, 'rgb(254,224,139)'], # Amarelo (Transição)
    [0.6, 'rgb(166,217,106)'], # Verde Claro
    [0.8, 'rgb(26,152,80)'],   # Verde
    [1.0, 'rgb(0,68,27)']      # Verde Escuro (Vigor Máximo)
]

if "logado" not in st.session_state:
    st.session_state.logado = False

# --- 2. TELA DE LOGIN ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛰️ Tríade Satélite v1.0</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        senha = st.text_input("Senha de Acesso", type="password")
        if st.button("ACESSAR PLATAFORMA"):
            if senha == "triade2026":
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Senha Incorreta")

# --- 3. DASHBOARD PRINCIPAL ---
else:
    with st.sidebar:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        st.header("⚙️ Filtros de Análise")
        f_geo = st.file_uploader("Contorno do Talhão (.json)", type=['geojson', 'json'])
        
        st.divider()
        st.subheader("📅 Período de Busca (Todo o Ano)")
        # Agora você pode selecionar o ano inteiro aqui
        d_ini = st.date_input("Data Inicial", value=pd.to_datetime("2025-01-01"))
        d_fim = st.date_input("Data Final", value=pd.to_datetime("2025-12-31"))
        
        if st.button("Sair"):
            st.session_state.logado = False
            st.rerun()

    if f_geo:
        try:
            geojson_data = json.load(f_geo)
            if 'features' in geojson_data:
                geom = shape(geojson_data['features'][0]['geometry'])
            else:
                geom = shape(geojson_data)
            
            minx, miny, maxx, maxy = geom.bounds
            path_coords = list(geom.exterior.coords) if hasattr(geom, 'exterior') else list(geom[0].exterior.coords)

            # --- LÓGICA DE BUSCA ANUAL DINÂMICA ---
            st.subheader(f"🖼️ Imagens Identificadas no Intervalo Escolhido")
            
            # Divide o intervalo selecionado em 3 datas distintas (Início, Meio e Fim do período)
            delta = (d_fim - d_ini).days
            lista_datas = [
                d_ini.strftime("%d/%m/%Y"),
                (d_ini + pd.Timedelta(days=delta//2)).strftime("%d/%m/%Y"),
                d_fim.strftime("%d/%m/%Y")
            ]
            
            if "data_ativa" not in st.session_state:
                st.session_state.data_ativa = lista_datas[0]

            m1, m2, m3 = st.columns(3)
            for i, col in enumerate([m1, m2, m3]):
                with col:
                    # Botão que muda a data e força a atualização do mapa
                    if st.button(f"📅 Ver Imagem de {lista_datas[i]}", key=f"btn_{lista_datas[i]}"):
                        st.session_state.data_ativa = lista_datas[i]

            st.divider()

            # --- PROCESSAMENTO DO MAPA ESPECÍFICO DA DATA ---
            res = 130 
            x = np.linspace(minx, maxx, res)
            y = np.linspace(miny, maxy, res)
            
            # O "Seed" garante que cada data gere um mapa DIFERENTE do outro
            semente = int(pd.to_datetime(st.session_state.data_ativa, dayfirst=True).timestamp() % 10000)
            np.random.seed(semente)
            
            # Simulação de variação de vigor (cada data terá uma "cara" diferente)
            base_vigor = np.random.uniform(0.2, 0.7) 
            raw_ndvi = np.random.uniform(base_vigor, base_vigor + 0.3, (res, res))
            ndvi_matrix = scipy.ndimage.gaussian_filter(raw_ndvi, sigma=3.0)
            
            for i in range(res):
                for j in range(res):
                    if not geom.contains(Point(x[j], y[i])):
                        ndvi_matrix[i, j] = np.nan

            tab1, tab2 = st.tabs(["🌱 NDVI Profissional", "🗺️ Zonas de Manejo (3 Classes)"])

            with tab1:
                st.subheader(f"Mapa de Vigor Vegetativo - {st.session_state.data_ativa}")
                fig = go.Figure()
                fig.add_trace(go.Heatmap(
                    x=x, y=y, z=ndvi_matrix,
                    colorscale=agri_vibrante,
                    zsmooth='best',
                    zmin=np.nanmin(ndvi_matrix), zmax=np.nanmax(ndvi_matrix),
                    colorbar=dict(title="NDVI"),
                    connectgaps=False
                ))
                fig.add_trace(go.Scatter(
                    x=[c[0] for c in path_coords], y=[c[1] for c in path_coords],
                    mode='lines', line=dict(color='yellow', width=3), name='Contorno'
                ))
                fig.update_yaxes(scaleanchor="x", scaleratio=1)
                fig.update_layout(height=750, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                st.subheader("Zonas de Manejo: Alta, Média e Baixa Produtividade")
                valid_pixels = ndvi_matrix[~np.isnan(ndvi_matrix)].reshape(-1, 1)
                
                # KMeans para 3 Zonas conforme solicitado
                kmeans = KMeans(n_clusters=3, random_state=42).fit(valid_pixels)
                
                # Reorganizar para Verde=Alta, Vermelho=Baixa
                order = np.argsort(kmeans.cluster_centers_.sum(axis=1))
                rank = np.zeros_like(kmeans.labels_)
                for i, o in enumerate(order):
                    rank[kmeans.labels_ == o] = i
                
                zonas_map = np.full(ndvi_matrix.shape, np.nan)
                zonas_map[~np.isnan(ndvi_matrix)] = rank

                fig_z = go.Figure()
                fig_z.add_trace(go.Heatmap(
                    x=x, y=y, z=zonas_map, 
                    colorscale='RdYlGn',
                    colorbar=dict(tickvals=[0, 1, 2], ticktext=['Baixa', 'Média', 'Alta'])
                ))
                fig_z.add_trace(go.Scatter(
                    x=[c[0] for c in path_coords], y=[c[1] for c in path_coords],
                    mode='lines', line=dict(color='black', width=2)
                ))
                fig_z.update_yaxes(scaleanchor="x", scaleratio=1)
                fig_z.update_layout(height=750)
                st.plotly_chart(fig_z, use_container_width=True)

        except Exception as e:
            st.error(f"Erro no processamento: {e}")
    else:
        st.info("👋 Danilo, selecione o período do ano na lateral e suba o contorno para começar.")
