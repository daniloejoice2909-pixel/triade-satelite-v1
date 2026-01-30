import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.cluster import KMeans
import os

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(layout="wide", page_title="Tríade Satélite & Zonas de Manejo")

# Estilo para manter o padrão visual
st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .stButton>button { width: 100%; background-color: #388E3C; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGICA DE LOGIN (Padrão Triade) ---
if "logado" not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    st.markdown("<h1 style='text-align:center;'>🛰️ Tríade Satélite v1.0</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if os.path.exists("LogoTriadeagro.png.png"): st.image("LogoTriadeagro.png.png")
        senha = st.text_input("Acesso Satelital", type="password")
        if st.button("DESBLOQUEAR PLATAFORMA"):
            if senha == "triade2026":
                st.session_state.logado = True
                st.rerun()
else:
    # --- 3. BARRA LATERAL ---
    with st.sidebar:
        st.header("📍 Configuração do Talhão")
        produtor = st.text_input("Produtor", "Danilo")
        fazenda = st.text_input("Fazenda")
        st.markdown("---")
        data_ini = st.date_input("Data Inicial da Busca")
        data_fim = st.date_input("Data Final da Busca")
        st.info("O sistema buscará imagens do Sentinel-2 com menor índice de nuvens no período.")

    # --- 4. ABAS DE TRABALHO ---
    tab_sat, tab_zonas, tab_export = st.tabs(["🛰️ SENSORIAMENTO", "🗺️ ZONAS DE PRODUTIVIDADE", "📦 EXPORTAÇÃO TV"])

    with tab_sat:
        st.subheader("Processamento de Índices de Vegetação")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Resolução", "10m (Sentinel-2)")
        c2.metric("Índice Ativo", "NDVI")
        
        st.markdown("### Selecionar Camadas para Composição")
        st.write("Escolha as imagens para calcular a **Fidelidade de Manejo**:")
        
        # Simulação de seleção de datas de imagens disponíveis
        img1 = st.checkbox("Imagem 12/01/2026 (Nuvens: 2%)", value=True)
        img2 = st.checkbox("Imagem 05/01/2026 (Nuvens: 0%)", value=True)
        img3 = st.checkbox("Imagem 28/12/2025 (Nuvens: 5%)")

        if st.button("PROCESSAR MÉDIA E FIDELIDADE"):
            with st.spinner("Analisando pixel a pixel..."):
                # Simulação de cálculo de fidelidade entre imagens
                fidelidade = 92.5
                st.success(f"Fidelidade entre imagens: {fidelidade}%")
                st.caption("Fidelidade alta indica que a variabilidade é real da planta e não interferência externa.")

    with tab_zonas:
        st.subheader("Definição de Zonas de Manejo")
        st.write("O sistema divide o talhão em **3 zonas** baseadas no potencial produtivo histórico.")
        
        # Criando dados fictícios para visualização do mapa de zonas
        x = np.linspace(0, 10, 50)
        y = np.linspace(0, 10, 50)
        X, Y = np.meshgrid(x, y)
        Z = np.sin(X)*0.5 + np.cos(Y)*0.5 + np.random.rand(50,50)*0.2
        
        # Lógica de Clusterização (K-Means) para 3 zonas
        dados_pixel = Z.flatten().reshape(-1, 1)
        kmeans = KMeans(n_clusters=3, random_state=42).fit(dados_pixel)
        zonas = kmeans.labels_.reshape(50, 50)

        fig = go.Figure(data=go.Heatmap(
            z=zonas,
            colorscale=[[0, 'red'], [0.5, 'yellow'], [1, 'green']],
            showscale=False
        ))
        
        fig.update_layout(
            title="Mapa de Zonas: Alta (Verde), Média (Amarelo), Baixa (Vermelho)",
            xaxis=dict(visible=False), yaxis=dict(visible=False)
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 📍 Pontos de Amostragem Georreferenciados")
        num_pontos = st.slider("Número de pontos por zona", 5, 50, 20)
        if st.button("GERAR PONTOS ALEATÓRIOS (Distância > 30m)"):
            st.info(f"Gerando {num_pontos*3} pontos respeitando as divisas entre zonas...")

    with tab_export:
        st.subheader("Gerar Arquivos para o Monitor")
        tipo_maquina = st.selectbox("Marca do Monitor/Trator", ["John Deere (Shapefile)", "Case IH (CN1)", "Trimble", "New Holland"])
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**🌱 Sementes (RSTV)**")
            v1 = st.number_input("Zona Alta (sem/ha)", value=75000)
            v2 = st.number_input("Zona Média (sem/ha)", value=68000)
        with c2:
            st.markdown("**🧪 Nitrogênio (RNTV)**")
            n1 = st.number_input("Zona Alta (kg/ha)", value=150)
            n2 = st.number_input("Zona Média (kg/ha)", value=120)
        with c3:
            st.markdown("**💦 Dessecação (RDTV)**")
            v_vazao = st.number_input("Vazão Zona Alta (L/ha)", value=100)

        if st.button("📦 EXPORTAR PACOTE DE PRESCRIÇÃO"):
            st.success(f"Arquivo preparado para {tipo_maquina}. Pronto para download.")
