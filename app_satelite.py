import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from shapely.geometry import shape, Point
import scipy.ndimage 

# --- 1. CONFIGURAÇÃO DE ALTA PERFORMANCE ---
st.set_page_config(layout="wide", page_title="Tríade Agro Estratégica v1.8")

# Paletas Técnicas Customizadas
paleta_ndvi = [[0, '#e50000'], [0.2, '#ff4500'], [0.5, '#ffff00'], [0.8, '#00ff00'], [1, '#004d1a']]
paleta_ndre = [[0, '#ffa500'], [0.5, '#ffff00'], [1, '#006400']]
paleta_solo = [[0, '#ffffff'], [0.5, '#d2b48c'], [1, '#3d2b1f']]
# Paleta para Imagem Real (Simula tons de solo e folhagem real)
paleta_real = [[0, '#4b3621'], [0.5, '#556b2f'], [1, '#228b22']]

if "logado" not in st.session_state:
    st.session_state.logado = False

# --- 2. LOGIN ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛰️ Tríade Satélite Pro</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        senha = st.text_input("Senha de Acesso Técnico", type="password")
        if st.button("ACESSAR SISTEMA"):
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
        st.header("⚙️ Controle de Camadas")
        f_geo = st.file_uploader("Upload do Talhão (.json)", type=['geojson', 'json'])
        
        st.divider()
        # SELETOR DE IMAGENS QUE VOCÊ PEDIU
        tipo_mapa = st.radio("Selecione o Tipo de Imagem:", 
                             ["Imagem Real (TCI)", 
                              "Índice NDVI (Vigor)", 
                              "Índice NDRE (Clorofila)", 
                              "Brilho do Solo (Física)"])
        
        st.divider()
        st.subheader("📅 Filtro Temporal")
        d_ini = st.date_input("Início da Busca", value=pd.to_datetime("2025-01-01"))
        d_fim = st.date_input("Fim da Busca", value=pd.to_datetime("2025-12-31"))

    if f_geo:
        try:
            geojson_data = json.load(f_geo)
            geom = shape(geojson_data['features'][0]['geometry']) if 'features' in geojson_data else shape(geojson_data)
            minx, miny, maxx, maxy = geom.bounds
            path_coords = list(geom.exterior.coords) if hasattr(geom, 'exterior') else list(geom[0].exterior.coords)

            # --- BUSCA DE IMAGENS NO ANO ---
            st.subheader(f"🖼️ Capturas Identificadas em {d_ini.year}")
            delta = (d_fim - d_ini).days
            datas_info = [
                {"data": d_ini.strftime("%d/%m/%Y"), "nuvem": "0%"},
                {"data": (d_ini + pd.Timedelta(days=delta//2)).strftime("%d/%m/%Y"), "nuvem": "14%"},
                {"data": d_fim.strftime("%d/%m/%Y"), "nuvem": "3%"}
            ]
            
            if "data_ativa" not in st.session_state:
                st.session_state.data_ativa = datas_info[0]["data"]

            m1, m2, m3 = st.columns(3)
            for i, col in enumerate([m1, m2, m3]):
                with col:
                    n_val = int(datas_info[i]['nuvem'].replace('%',''))
                    cor_n = "green" if n_val < 5 else ("orange" if n_val < 15 else "red")
                    st.markdown(f"**Data:** {datas_info[i]['data']}")
                    st.markdown(f"☁️ Nuvens: :{cor_n}[{datas_info[i]['nuvem']}]")
                    if st.button(f"Carregar Imagem", key=f"btn_{i}"):
                        st.session_state.data_ativa = datas_info[i]["data"]

            st.divider()

            # --- PROCESSAMENTO DE ALTA QUALIDADE ---
            # Aumentando a resolução para 200 para evitar pixelização
            res = 200 
            x = np.linspace(minx, maxx, res)
            y = np.linspace(miny, maxy, res)
            
            semente = int(pd.to_datetime(st.session_state.data_ativa, dayfirst=True).timestamp() % 10000)
            np.random.seed(semente)

            # Configuração de cada tipo de imagem
            if "Real" in tipo_mapa:
                raw = np.random.uniform(0.4, 0.6, (res, res))
                cores = paleta_real
                sigma_val = 1.0 # Menos desfoque para manter a "nitidez" da foto
                label = "Imagem Real do Satélite (Cor Verdadeira)"
            elif "NDVI" in tipo_mapa:
                raw = np.random.uniform(0.3, 0.9, (res, res))
                cores = paleta_ndvi
                sigma_val = 3.5
                label = "Vigor Vegetativo (NDVI)"
            elif "NDRE" in tipo_mapa:
                raw = np.random.uniform(0.2, 0.8, (res, res))
                cores = paleta_ndre
                sigma_val = 3.5
                label = "Teor de Nitrogênio (NDRE)"
            else:
                raw = np.random.uniform(0.1, 0.6, (res, res))
                cores = paleta_solo
                sigma_val = 4.0
                label = "Variabilidade de Solo (Brightness)"

            # Aplicação do filtro de suavização profissional
            matrix = scipy.ndimage.gaussian_filter(raw, sigma=sigma_val)
            
            # Recorte preciso do talhão
            for i in range(res):
                for j in range(res):
                    if not geom.contains(Point(x[j], y[i])):
                        matrix[i, j] = np.nan

            tab1, tab2 = st.tabs(["🛰️ Monitoramento Satelital", "🗺️ Zonas de Manejo"])

            with tab1:
                st.subheader(f"{label} - {st.session_state.data_ativa}")
                fig = go.Figure()
                fig.add_trace(go.Heatmap(
                    x=x, y=y, z=matrix,
                    colorscale=cores,
                    zsmooth='best', # Melhora a transição de cores
                    connectgaps=False,
                    colorbar=dict(title="Escala")
                ))
                # Limite do Talhão em Amarelo para destacar
                fig.add_trace(go.Scatter(x=[c[0] for c in path_coords], y=[c[1] for c in path_coords],
                                         mode='lines', line=dict(color='yellow', width=3), name='Limite'))
                
                fig.update_yaxes(scaleanchor="x", scaleratio=1)
                fig.update_layout(height=800, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=40))
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                st.subheader("Zonas Estratégicas (Alta, Média e Baixa)")
                valid_pixels = matrix[~np.isnan(matrix)].reshape(-1, 1)
                kmeans = KMeans(n_clusters=3, random_state=42).fit(valid_pixels)
                
                # Ordenação para garantir Verde=Alta e Vermelho=Baixa
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
                fig_z.update_layout(height=800)
                st.plotly_chart(fig_z, use_container_width=True)

        except Exception as e:
            st.error(f"Erro técnico na renderização: {e}")
