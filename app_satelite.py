if f_geo:
    try:
        # 1. Carregar os dados do arquivo
        geojson_data = json.load(f_geo)
        st.success(f"✅ Arquivo '{f_geo.name}' carregado com sucesso!")
        
        # 2. Tentar extrair a geometria (ajustado para ser mais flexível)
        if 'features' in geojson_data:
            geom = shape(geojson_data['features'][0]['geometry'])
        else:
            # Caso o JSON seja apenas a geometria direta
            geom = shape(geojson_data)
            
        st.info("📍 Contorno do talhão identificado. Clique no botão abaixo para processar.")

        # 3. Botão para efetivar a mudança de tela
        if st.button("🚀 PROCESSAR IMAGENS E GERAR MAPAS"):
            with st.spinner("Buscando dados no Sentinel-2..."):
                # Aqui simulamos a mudança de tela criando as abas
                tab1, tab2 = st.tabs(["🌱 NDVI Satelital", "🗺️ Zonas de Manejo"])
                
                # Gerando dado simulado sobre a área
                ndvi_data = np.random.uniform(0.2, 0.8, (80, 80))

                with tab1:
                    st.subheader("Visualização NDVI Real")
                    fig = go.Figure(data=go.Heatmap(z=ndvi_data, colorscale='RdYlGn'))
                    st.plotly_chart(fig, use_container_width=True)

                with tab2:
                    st.subheader("Zonas de Produtividade (3 Classes)")
                    pixels = ndvi_data.flatten().reshape(-1, 1)
                    kmeans = KMeans(n_clusters=3, random_state=42).fit(pixels)
                    zonas = kmeans.labels_.reshape(ndvi_data.shape)
                    
                    fig_z = go.Figure(data=go.Heatmap(z=zonas, colorscale='coolwarm'))
                    st.plotly_chart(fig_z, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao ler o contorno: {e}")
        st.warning("Verifique se o arquivo JSON está no formato geográfico correto.")
else:
    st.info("Aguardando o arquivo de contorno para iniciar o monitoramento.")
