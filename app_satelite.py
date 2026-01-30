# Definindo a paleta clássica de monitoramento agrícola
# Vermelho -> Laranja -> Amarelo -> Verde Claro -> Verde Escuro
agri_colors = [
    [0.0, 'rgb(165,0,38)'],   # Vermelho Intenso (Solo/Morte)
    [0.2, 'rgb(215,48,39)'],  # Vermelho
    [0.4, 'rgb(254,224,139)'],# Amarelo (Transição)
    [0.6, 'rgb(166,217,106)'],# Verde Claro (Vigor Médio)
    [0.8, 'rgb(26,152,80)'],  # Verde (Vigor Alto)
    [1.0, 'rgb(0,68,27)']     # Verde Escuro (Máximo Vigor)
]

with tab1:
    st.subheader(f"Análise de Vigor Vegetativo - {st.session_state.data_ativa['data']}")
    fig = go.Figure()
    
    # Calculando os limites reais para dar contraste (Estiramento)
    v_min = np.nanmin(ndvi_matrix)
    v_max = np.nanmax(ndvi_matrix)

    fig.add_trace(go.Heatmap(
        x=x, y=y, z=ndvi_matrix,
        colorscale=agri_colors, # Aplicando a paleta profissional
        zmin=v_min, # O menor valor do talhão vira a cor mais baixa
        zmax=v_max, # O maior valor vira a cor mais alta
        connectgaps=False,
        hoverinfo='z'
    ))
