import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from shapely.geometry import shape

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(layout="wide", page_title="Tríade Agro Estratégica")

# Estilo para o mapa ficar grande e visível
st.markdown("<style> .main {overflow: hidden;} </style>", unsafe_allow_html=True)

if "logado" not in st.session_state:
    st.session_state.logado = False

# --- 2. TELA DE LOGIN ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛰️ Tríade Satélite v1.0</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        senha = st.text_input("Acesso Satelital", type="password")
        if st.button("DESBLOQUEAR PLATAFORMA"):
            if senha == "triade2026":
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Senha Incorreta")

# --- 3. PLATAFORMA PÓS-LOGIN ---
else:
    with st.sidebar:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        st.header("📍 Painel de Controle")
        
        f_geo = st.file_uploader("Subir Contorno do Talhão", type=['geojson', 'json'])
        
        st.subheader("📅 Seleção de Imagem")
        data_sel = st.selectbox("Imagens Disponíveis", 
                                ["30/01/2026 - (SkySat 0% Nuvens)", 
                                 "25/01/2026 - (Sentinel 5% Nuvens)", 
                                 "20/01/2026 - (Sentinel 12% Nuvens)"])
        
        if st.button("Sair"):
            st.session_state.logado = False
            st.rerun()

    # Área Principal
    if f_geo:
        try:
            geojson_data = json.load(f_geo)
            
            # Extração segura das coordenadas
            if 'features' in geojson_data:
                coords = geojson_data['features'][0]['geometry']['coordinates'][0]
            else:
                coords = geojson_data['coordinates'][0]
            
            # Ajuste de escala para o gráfico (normalizando para 0-100)
            path_x = np.array([c[0] for c in coords])
            path_y = np.array([c[1] for c in coords])
            
            # Normalização simples para sobrepor na matriz do mapa
            x_norm = (path_x - path_x.min()) / (path_x.max() - path_x.min()) * 100
            y_norm = (path_y - path_y.min()) / (path_y.max() - path_y.min()) * 100

            st.success(f"✅ Talhão '{f_geo.name}' carregado!")

            if st.button("🚀 PROCESSAR NDVI E GERAR ZONAS"):
                with st.spinner("Gerando visualização de alta definição..."):
                    
                    # Simulação de NDVI com "ruído" mais realista (mais nítido)
                    ndvi_matrix = np.random.uniform(0.3, 0.85, (100, 100))
                    
                    tab1, tab2 = st.tabs(["🌱 Mapa de NDVI", "🗺️ 6 Zonas de Manejo"])

                    with tab1:
                        st.subheader(f"Vigor Vegetativo - {data_sel}")
                        fig = go.Figure()
                        # Mapa de Calor
                        fig.add_trace(go.Heatmap(
                            z=ndvi_matrix,
                            colorscale='RdYlGn',
                            zmin=0.2, zmax=0.9,
                            colorbar=dict(title="NDVI")
                        ))
                        # Linha de Contorno (O que você pediu)
                        fig.add_trace(go.Scatter(
                            x=x_norm, y=y_norm,
                            mode='lines',
                            line=dict(color='white', width=4), # Branco para destacar no verde/vermelho
                            name='Contorno do Talhão'
                        ))
                        fig.update_layout(height=700, template="plotly_dark")
                        st.plotly_chart(fig, use_container_width=True)

                    with tab2:
                        st.subheader("Mapa de Recomendação (6 Zonas)")
                        pixels = ndvi_matrix.flatten().reshape(-1, 1)
                        kmeans = KMeans(n_clusters=6, random_state=42).fit(pixels)
                        zonas = kmeans.labels_.reshape(ndvi_matrix.shape)
                        
                        fig_z = go.Figure()
                        fig_z.add_trace(go.Heatmap(
                            z=zonas, 
                            colorscale='RdYlGn'
                        ))
                        # Contorno também nas zonas
                        fig_z.add_trace(go.Scatter(
                            x=x_norm, y=y_norm,
                            mode='lines',
                            line=dict(color='black', width=3),
                            name='Contorno'
                        ))
                        fig_z.update_layout(height=700)
                        st.plotly_chart(fig_z, use_container_width=True)
                        
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {e}")
    else:
        st.info("👋 Olá Danilo! Por favor, faça o upload do contorno (.json) na barra lateral para visualizar as imagens.")
