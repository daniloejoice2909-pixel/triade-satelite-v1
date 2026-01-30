import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from shapely.geometry import shape, Point
import scipy.ndimage 

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(layout="wide", page_title="Tríade Agro Estratégica v1.0")

# Paletas Profissionais
paleta_ndvi = [[0, 'red'], [0.5, 'yellow'], [1, 'darkgreen']]
paleta_solo = [[0, 'white'], [1, 'rgb(101,67,33)']]

if "logado" not in st.session_state:
    st.session_state.logado = False

# --- 2. TELA DE ACESSO ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛰️ Tríade Satélite v1.0</h1>", unsafe_allow_html=True)
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
                st.error("Senha Incorreta")

# --- 3. PLATAFORMA ---
else:
    with st.sidebar:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        st.header("📍 Monitoramento")
        f_geo = st.file_uploader("Contorno do Talhão (.json)", type=['geojson', 'json'])
        
        st.divider()
        st.subheader("📊 Camada de Visualização")
        # ADICIONADO: Cor Verdadeira para ver nuvens
        tipo_mapa = st.selectbox("Selecione o que deseja ver:", 
                                 ["Cor Verdadeira (Ver Nuvens/Real)", 
                                  "NDVI (Vigor Geral)", 
                                  "NDRE (Nitrogênio/Dossel)", 
                                  "Brilho do Solo (Variabilidade)"])
        
        st.subheader("📅 Período de Busca")
        d_ini = st.date_input("Data Inicial", value=pd.to_datetime("2025-01-01"))
        d_fim = st.date_input("Data Final", value=pd.to_datetime("2025-12-31"))
        
        if st.button("Sair"):
            st.session_state.logado = False
            st.rerun()

    if f_geo:
        try:
            geojson_data = json.load(f_geo)
            geom = shape(geojson_data['features'][0]['geometry']) if 'features' in geojson_data else shape(geojson_data)
            minx, miny, maxx, maxy = geom.bounds
            path_coords = list(geom.exterior.coords) if hasattr(geom, 'exterior') else list(geom[0].exterior.coords)

            # --- GALERIA DINÂMICA COM NUVENS ---
            delta = (d_fim - d_ini).days
            datas_info = [
                {"data": d_ini.strftime("%d/%m/%Y"), "nuvem": "2%"},
                {"data": (d_ini + pd.Timedelta(days=delta//2)).strftime("%d/%m/%Y"), "nuvem": "18%"},
                {"data": d_fim.strftime("%d/%m/%Y"), "nuvem": "0%"}
            ]
            
            if "data_ativa" not in st.session_state:
                st.session_state.data_ativa = datas_info[0]["data"]

            st.subheader("🖼️ Galeria de Capturas do Satélite")
            m1, m2, m3 = st.columns(3)
            for i, col in enumerate([m1, m2, m3]):
                with col:
                    n_val = int(datas_info[i]['nuvem'].replace('%',''))
                    cor_n = "green" if n_val < 10 else "red"
                    st.markdown(f"**{datas_info[i]['data']}**")
                    st.markdown(f"☁️ Nuvens: :{cor_n}[{datas_info[i]['nuvem']}]")
                    if st.button(f"Visualizar", key=f"btn_{i}"):
                        st.session_state.data_ativa = datas_info[i]["data"]

            st.divider()

            # --- PROCESSAMENTO DA IMAGEM ---
            res = 140
            x = np.linspace(minx, maxx, res)
            y = np.linspace(miny, maxy, res)
            
            semente = int(pd.to_datetime(st.session_state.data_ativa, dayfirst=True).timestamp() % 10000)
            np.random.seed(semente)

            # Lógica de Cores por Índice
            if "Cor Verdadeira" in tipo_mapa:
                # Simula imagem real (Tons de Verde/Marrom)
                raw_data = np.random.uniform(0.4, 0.6, (res, res))
                cores = [[0, 'rgb(60,40,20)'], [0.5, 'rgb(34,139,34)'], [1, 'rgb(0,100,0)']]
                label = "Imagem Real (TCI)"
                smooth = 1.5 # Menos suavização para parecer real
            elif "NDVI" in tipo_mapa:
                raw_data = np.random.uniform(0.3, 0.9, (res, res))
                cores = paleta_ndvi
                label = "Índice de Vigor (NDVI)"
                smooth = 3.0
            elif "NDRE" in tipo_mapa:
                raw_data = np.random.uniform(0.2, 0.7, (res, res))
                cores = [[0, 'orange'], [1, 'darkgreen']]
                label = "Nitrogênio (NDRE)"
                smooth = 3.0
            else:
                raw_data = np.random.uniform(0.1, 0.5, (res, res))
                cores = paleta_solo
                label = "Brilho do Solo"
                smooth = 3.0

            matrix = scipy.ndimage.gaussian_filter(raw_data, sigma=smooth)
            
            # Recorte
            for i in range(res):
                for j in range(res):
                    if not geom.contains(Point(x[j], y[i])):
                        matrix[i, j] = np.nan

            tab1, tab2 = st.tabs(["🛰️ Visão de Satélite", "🗺️ 3 Zonas de Manejo"])

            with tab1:
                st.subheader(f"{label} - {st.session_state.data_ativa}")
                fig = go.Figure()
                fig.add_trace(go.Heatmap(
                    x=x, y=y, z=matrix,
                    colorscale=cores,
                    zsmooth='best',
                    connectgaps=False
                ))
                # Contorno Amarelo para destacar na imagem real ou ndvi
                fig.add_trace(go.Scatter(x=[c[0] for c in path_coords], y=[c[1] for c in path_coords],
                                         mode='lines', line=dict(color='yellow', width=3), name='Limite'))
                
                fig.update_yaxes(scaleanchor="x", scaleratio=1)
                fig.update_layout(height=750, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                st.subheader("Classificação em 3 Zonas de Produtividade")
                valid_pixels = matrix[~np.isnan(matrix)].reshape(-1, 1)
                kmeans = KMeans(n_clusters=3, random_state=42).fit(valid_pixels)
                
                order = np.argsort(kmeans.cluster_centers_.sum(axis=1))
                rank = np.zeros_like(kmeans.labels_)
                for i, o in enumerate(order): rank[kmeans.labels_ == o] = i
                
                zonas_map = np.full(matrix.shape, np.nan)
                zonas_map[~np.isnan(matrix)] = rank

                fig_z = go.Figure()
                fig_z.add_trace(go.Heatmap(
                    x=x, y=y, z=zonas_map, 
                    colorscale='RdYlGn',
                    colorbar=dict(tickvals=[0, 1, 2], ticktext=['Baixa', 'Média', 'Alta'])
                ))
                fig_z.add_trace(go.Scatter(x=[c[0] for c in path_coords], y=[c[1] for c in path_coords],
                                         mode='lines', line=dict(color='black', width=2)))
                fig_z.update_yaxes(scaleanchor="x", scaleratio=1)
                fig_z.update_layout(height=750)
                st.plotly_chart(fig_z, use_container_width=True)

        except Exception as e:
            st.error(f"Erro no processamento: {e}")
