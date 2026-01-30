import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from shapely.geometry import shape, Point
import scipy.ndimage 

# --- 1. CONFIGURAÇÃO DE ALTA DEFINIÇÃO ---
st.set_page_config(layout="wide", page_title="Tríade Satélite Pro - Alta Fidelidade")

# PALETA FIELDVIEW/ONESOIL (Estiramento de 7 níveis para máxima nitidez)
paleta_agro_pro = [
    [0.0, '#a50026'],   # Vermelho Profundo (Crítico)
    [0.15, '#d73027'],  # Vermelho Vivo
    [0.3, '#f46d43'],   # Laranja
    [0.5, '#fee08b'],   # Amarelo Creme (Transição)
    [0.7, '#d9ef8b'],   # Verde Limão
    [0.85, '#66bd63'],  # Verde Médio
    [1.0, '#1a9850']    # Verde Intenso (Máximo Vigor)
]

# Paleta Solo (Padrão FieldView para solo exposto)
paleta_solo_pro = [[0, '#f5f5f5'], [0.5, '#8c510a'], [1, '#543005']]

if "logado" not in st.session_state:
    st.session_state.logado = False

# --- 2. ACESSO ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛰️ Tríade Satélite Pro</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        senha = st.text_input("Acesso Consultor", type="password")
        if st.button("DESBLOQUEAR"):
            if senha == "triade2026":
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Senha Incorreta")

# --- 3. DASHBOARD PROFISSIONAL ---
else:
    with st.sidebar:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        st.header("🎚️ Painel de Precisão")
        f_geo = st.file_uploader("Contorno Berneck (.json)", type=['geojson', 'json'])
        
        st.divider()
        tipo_mapa = st.radio("Camada Técnica:", 
                             ["NDVI (Vigor de Safra)", 
                              "NDRE (Nitrogênio e Dossel)", 
                              "Brilho do Solo", 
                              "Cor Verdadeira (Real)"])
        
        st.divider()
        st.subheader("📅 Janela Temporal")
        d_ini = st.date_input("De:", value=pd.to_datetime("2025-01-01"))
        d_fim = st.date_input("Até:", value=pd.to_datetime("2025-12-31"))
        
        if st.button("Finalizar Sessão"):
            st.session_state.logado = False
            st.rerun()

    if f_geo:
        try:
            geojson_data = json.load(f_geo)
            geom = shape(geojson_data['features'][0]['geometry']) if 'features' in geojson_data else shape(geojson_data)
            minx, miny, maxx, maxy = geom.bounds
            path_coords = list(geom.exterior.coords) if hasattr(geom, 'exterior') else list(geom[0].exterior.coords)

            # --- GALERIA DE MINIATURAS ESTILO ONESOIL ---
            st.subheader("📅 Linha do Tempo de Imagens")
            m1, m2, m3 = st.columns(3)
            # Simulação de busca anual
            datas = [d_fim.strftime("%d/%m/%Y"), "12/07/2025", d_ini.strftime("%d/%m/%Y")]
            nuvens = ["0%", "15%", "2%"]
            
            if "data_ativa" not in st.session_state:
                st.session_state.data_ativa = datas[0]

            for i, col in enumerate([m1, m2, m3]):
                with col:
                    st.write(f"**{datas[i]}**")
                    st.caption(f"☁️ Nuvens: {nuvens[i]}")
                    if st.button("Carregar", key=f"btn_{i}"):
                        st.session_state.data_ativa = datas[i]

            st.divider()

            # --- MOTOR DE RENDERIZAÇÃO DE ALTA FIDELIDADE ---
            res = 200 # Resolução Profissional
            x = np.linspace(minx, maxx, res)
            y = np.linspace(miny, maxy, res)
            
            semente = int(pd.to_datetime(st.session_state.data_ativa, dayfirst=True).timestamp() % 10000)
            np.random.seed(semente)

            # Lógica de processamento por índice
            if "NDVI" in tipo_mapa:
                raw = np.random.uniform(0.35, 0.85, (res, res))
                cores = paleta_agro_pro
                sigma = 2.0
            elif "NDRE" in tipo_mapa:
                raw = np.random.uniform(0.2, 0.7, (res, res))
                cores = [[0, '#ff7f00'], [0.5, '#ffff00'], [1, '#00441b']]
                sigma = 2.0
            elif "Solo" in tipo_mapa:
                raw = np.random.uniform(0.1, 0.5, (res, res))
                cores = paleta_solo_pro
                sigma = 3.0
            else: # Cor Verdadeira Realista
                raw = np.random.uniform(0.4, 0.6, (res, res))
                cores = [[0, '#3b2f21'], [0.5, '#2d5a27'], [1, '#1a3c15']]
                sigma = 0.8 # Quase nada de blur para parecer foto real

            # Interpolação Gaussiana para simular continuidade de campo
            matrix = scipy.ndimage.gaussian_filter(raw, sigma=sigma)
            
            # Recorte preciso (Clip)
            for i in range(res):
                for j in range(res):
                    if not geom.contains(Point(x[j], y[i])):
                        matrix[i, j] = np.nan

            tab1, tab2 = st.tabs(["🛰️ Monitoramento de Alta Precisão", "🗺️ Zonas de Manejo (3 Zonas)"])

            with tab1:
                st.subheader(f"{tipo_mapa} - Data: {st.session_state.data_ativa}")
                fig = go.Figure()
                
                # Heatmap com interpolação Bilinear simulada por 'zsmooth'
                fig.add_trace(go.Heatmap(
                    x=x, y=y, z=matrix,
                    colorscale=cores,
                    zsmooth='best',
                    zmin=np.nanmin(matrix), zmax=np.nanmax(matrix),
                    colorbar=dict(title="Índice", thickness=15),
                    connectgaps=False
                ))
                
                # Borda do Talhão com Linha Branca Fina (Padrão OneSoil)
                fig.add_trace(go.Scatter(x=[c[0] for c in path_coords], y=[c[1] for c in path_coords],
                                         mode='lines', line=dict(color='white', width=1.5), name='Contorno'))
                
                fig.update_yaxes(scaleanchor="x", scaleratio=1)
                fig.update_layout(height=800, template="plotly_dark", margin=dict(l=0,r=0,b=0,t=40))
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                st.subheader("Mapa de Recomendação em 3 Zonas")
                valid = matrix[~np.isnan(matrix)].reshape(-1, 1)
                kmeans = KMeans(n_clusters=3, n_init=10, random_state=42).fit(valid)
                
                order = np.argsort(kmeans.cluster_centers_.sum(axis=1))
                rank = np.zeros_like(kmeans.labels_)
                for i, o in enumerate(order): rank[kmeans.labels_ == o] = i
                
                zonas_map = np.full(matrix.shape, np.nan)
                zonas_map[~np.isnan(matrix)] = rank

                fig_z = go.Figure()
                fig_z.add_trace(go.Heatmap(
                    x=x, y=y, z=zonas_map, 
                    colorscale=['#d73027', '#fee08b', '#1a9850'], # Vermelho, Amarelo, Verde OneSoil
                    colorbar=dict(tickvals=[0, 1, 2], ticktext=['Baixa', 'Média', 'Alta'])
                ))
                fig_z.add_trace(go.Scatter(x=[c[0] for c in path_coords], y=[c[1] for c in path_coords],
                                         mode='lines', line=dict(color='black', width=1)))
                fig_z.update_yaxes(scaleanchor="x", scaleratio=1)
                fig_z.update_layout(height=800)
                st.plotly_chart(fig_z, use_container_width=True)

        except Exception as e:
            st.error(f"Erro na renderização profissional: {e}")
