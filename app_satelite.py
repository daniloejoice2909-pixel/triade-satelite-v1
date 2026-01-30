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
st.set_page_config(layout="wide", page_title="Tríade Satélite Pro v11.1")

# Tons de Verde para Zonas de Manejo Homogêneas
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
    # --- 4. BARRA LATERAL (CHAVES RESTAURADAS) ---
    with st.sidebar:
        if os.path.exists("logoTriadetransparente.png"):
            st.image("logoTriadetransparente.png")
        
        st.header("🔑 Credenciais CDSE")
        # Campos de Chaves (Aparecem aqui novamente)
        c_id = st.text_input("Client ID", type="password", value=st.secrets.get("CLIENT_ID", ""))
        c_sec = st.text_input("Client Secret", type="password", value=st.secrets.get("CLIENT_SECRET", ""))
        
        st.divider()
        st.header("⚙️ Filtros de Pureza")
        f_geo = st.file_uploader("Contorno Berneck (.json)", type=['geojson', 'json'])
        
        filtro_pureza = st.checkbox("Remover Interferências (Poeira/Umidade)", value=True)
        suavidade = st.slider("Tamanho das Zonas (Padrão OneSoil)", 10.0, 40.0, 25.0)
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
        cols = st.columns(2
