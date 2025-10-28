# --- ARCHIVO: appv3.py ---
# (Guarda este archivo como app.py y ejecútalo con: streamlit run app.py)

import streamlit as st
import pandas as pd
import config         # Importa constantes
import data_loader    # Importa la carga de datos
import simulator      # Importa el motor de simulación
import ui_helpers     # Importa las funciones de gráficos y métricas
import altair as alt  # Importamos Altair

# ---------------------------------------------------------------------
# --- 1. LÓGICA DE LA PÁGINA DEL SIMULADOR ---
# ---------------------------------------------------------------------
def show_simulator():
    """
    Función que construye y ejecuta la interfaz de usuario del simulador.
    """
    
    # --- Configuración de Idioma y Título del Simulador ---
    ui_helpers.setup_locale() # Configura meses en español
    st.title("Simulador de Proyección de Inventario 📈")

    # Botón para volver al menú en la barra lateral
    st.sidebar.button("⬅️ Volver al Menú Principal", on_click=lambda: st.session_state.update(page='menu'))
    st.sidebar.markdown("---") # Separador

    # --- 2. Carga de Datos ---
    try:
        df_stock, df_oc, df_consumo, df_residencial = data_loader.load_data()
    except FileNotFoundError as e:
        st.error(f"Error Crítico: No se pudo encontrar el archivo: {e.filename}.")
        st.info("Por favor, asegúrese de que los archivos 'Stock.xlsx', 'OPOR.xlsx' y 'ST_OWTR.xlsx' estén en la misma carpeta que 'app.py'.")
        st.stop() # Detiene la ejecución de la app si faltan archivos
    except Exception as e:
        st.error(f"Ocurrió un error inesperado durante la carga de datos: {e}")
        st.stop()

    # --- 3. Construcción de la Barra Lateral (Sidebar) ---
    st.sidebar.header("Configuración de Simulación")

    # --- Listas para selectores ---
    lista_skus_stock = df_stock['CodigoArticulo'].dropna().unique()
    lista_skus_consumo = df_consumo['CodigoArticulo'].dropna().unique()
    all_skus = sorted(list(set(lista_skus_stock) | set(lista_skus_consumo)))
    
    lista_bodegas_stock = sorted(df_stock['CodigoBodega'].dropna().unique())
    lista_bodegas_consumo = sorted(df_consumo['BodegaDestino_Requerida'].dropna().unique())
    
    # --- Requerimiento 2: Selector de SKU (usando ui_helper) ---
    opciones_selector_sku, mapa_nombres, default_index = ui_helpers.create_sku_options(all_skus, df_stock)
    
    sku_seleccionado_formateado = st.sidebar.selectbox(
        "1. Seleccione un SKU (busque por código o nombre):",
        opciones_selector_sku, 
        index=default_index
    )
    sku_seleccionado = sku_seleccionado_formateado.split(" | ")[0]
    
    # --- Otros Selectores ---
    bodega_stock_sel = st.sidebar.selectbox(
        "2. Seleccione Bodega de Stock:",
        lista_bodegas_stock,
        index=lista_bodegas_stock.index('BF0001') if 'BF0001' in lista_bodegas_stock else 0
    )
    
    bodega_consumo_sel = st.sidebar.selectbox(
        "3. Seleccione Bodega de Consumo:",
        lista_bodegas_consumo,
        index=lista_bodegas_consumo.index('Bodega de Proyectos RE') if 'Bodega de Proyectos RE' in lista_bodegas_consumo else 0
    )
    
    st.sidebar.markdown("---")
    
    # --- Parámetros de Simulación ---
    service_level_str = st.sidebar.select_slider(
        "4. Nivel de Servicio (para Safety Stock):",
        options=list(config.Z_SCORE_MAP.keys()),
        value="99%"
    )
    service_level_z = config.Z_SCORE_MAP[service_level_str]
    
    lead_time_days = st.sidebar.number_input("5. Lead Time (Días):", min_value=1, max_value=120, value=90)
    
    dias_a_simular = st.sidebar.number_input("6. Días a Simular:", min_value=30, max_value=365, value=90)
    
    
    # --- 4. Disparador de Ejecución ---
    if st.sidebar.button("🚀 Ejecutar Simulación", type="primary"):
        with st.spinner("Calculando simulación..."):
            
            # --- A. Ejecutar Simulación ---
            df_sim, metrics, llegadas_map, df_llegadas_detalle = simulator.run_inventory_simulation(
                sku_to_simulate=sku_seleccionado,
                warehouse_code=bodega_stock_sel,
                consumption_warehouse=bodega_consumo_sel,
                df_stock_raw=df_stock,
                df_consumo_raw=df_consumo,
                df_oc_raw=df_oc,
                simulation_days=dias_a_simular,
                lead_time_days=lead_time_days,
                service_level_z=service_level_z
            )
            
            # --- B. Mostrar Métricas ---
            st.subheader(f"Resultados para: {sku_seleccionado}")
            st.caption(f"Nombre: {mapa_nombres.get(sku_seleccionado, 'N/A')}")
            ui_helpers.display_metrics(metrics, lead_time_days, service_level_z)
            
            # --- C. Mostrar Recomendación de Pedido ---
            st.markdown("---") # Separador
            ui_helpers.display_order_recommendation(metrics, llegadas_map)

            # --- D. Mostrar Detalle de Llegadas ---
            st.markdown("---") # Separador
            ui_helpers.display_arrival_details(df_llegadas_detalle)

            st.markdown("---") # Separador
            
            # --- E. Generar y Mostrar Gráfico ---
            sku_name = mapa_nombres.get(sku_seleccionado, sku_seleccionado)
            fig = ui_helpers.generate_simulation_plot(
                df_sim, 
                metrics, 
                llegadas_map, 
                sku_name, 
                dias_a_simular
            )
            # (Usamos st.altair_chart en lugar de st.pyplot)
            st.altair_chart(fig, use_container_width=True)
            
            # --- F. Mostrar Tabla Fin de Mes (Req. 3) ---
            df_tabla_resultados = ui_helpers.prepare_end_of_month_table(df_sim)
            st.subheader("Stock Simulado a Fin de Mes")
            st.dataframe(df_tabla_resultados, use_container_width=True, hide_index=True)
            
    else:
        # Mensaje de bienvenida inicial
        st.info("Ajuste los parámetros en la barra lateral y presione 'Ejecutar Simulación'")

# ---------------------------------------------------------------------
# --- 2. LÓGICA DE LA PÁGINA DEL MENÚ PRINCIPAL ---
# ---------------------------------------------------------------------
def show_main_menu():
    """
    Muestra la pantalla del menú principal.
    """
    
    # --- MOSTRAR IMAGEN DE PORTADA ---
    try:
        col1, col_img, col3 = st.columns([1, 2, 1])
        with col_img: 
            st.image("COPEC-FLUX.svg", use_container_width=True)
    except FileNotFoundError:
        st.warning("No se encontró el archivo 'logo_empresa.png'. Asegúrate de agregarlo a la carpeta.")
    except Exception as e:
        st.error(f"No se pudo cargar la imagen: {e}")

    st.title("Menú Principal de Abastecimiento")
    st.markdown("Seleccione la herramienta que desea utilizar:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📈 Simulador de Proyección de Inventario", type="primary", use_container_width=True):
            st.session_state.page = 'simulator'
            st.rerun() 

    with col2:
        if st.button("📦 Consultar Próximas Llegadas", type="secondary", use_container_width=True):
            st.session_state.page = 'arrivals'
            st.rerun()


    # --- PRÓXIMAMENTE ---
    st.write("") # Espacio
    st.subheader("Próximamente")
    col1, col2 = st.columns(2)
    col1.button("📊 Dashboard de Ventas", disabled=True, use_container_width=True)
    col2.button("⚙️ Configuración", disabled=True, use_container_width=True)


# ---------------------------------------------------------------------
# --- 3. LÓGICA DE LA PÁGINA DE PRÓXIMAS LLEGADAS (MODIFICADA) ---
# ---------------------------------------------------------------------
def show_arrivals_page():
    """
    Muestra una página para consultar las próximas llegadas por SKU y/o OC.
    """
    st.title("Consulta de Próximas Llegadas 📦")

    # Botón para volver al menú en la barra lateral
    st.sidebar.button("⬅️ Volver al Menú Principal", on_click=lambda: st.session_state.update(page='menu'))
    st.sidebar.markdown("---")

    # --- 1. Carga de Datos ---
    try:
        df_stock, df_oc, df_consumo, df_residencial = data_loader.load_data()
    except FileNotFoundError as e:
        st.error(f"Error Crítico: No se pudo encontrar el archivo: {e.filename}.")
        st.stop()
    except Exception as e:
        st.error(f"Ocurrió un error inesperado durante la carga de datos: {e}")
        st.stop()

    # --- 2. Crear Selectores de Filtro ---
    
    # ----- INICIO DE LA MODIFICACIÓN -----
    
    # Listas para el selector de SKU
    lista_skus_stock = df_stock['CodigoArticulo'].dropna().unique()
    lista_skus_consumo = df_consumo['CodigoArticulo'].dropna().unique()
    all_skus = sorted(list(set(lista_skus_stock) | set(lista_skus_consumo)))
    
    opciones_selector_sku, mapa_nombres, _ = ui_helpers.create_sku_options(all_skus, df_stock)
    
    # Añadimos la opción "Todas" al selector de SKU
    opciones_con_todas = ["Todas"] + opciones_selector_sku
    
    # Creamos columnas para los filtros
    col1, col2 = st.columns(2)
    
    with col1:
        sku_seleccionado_formateado = st.selectbox(
            "Filtrar por SKU:",
            opciones_con_todas, 
            index=0, # Por defecto muestra "Todas"
            help="Seleccione el producto para ver sus Órdenes de Compra futuras."
        )
        sku_seleccionado = sku_seleccionado_formateado.split(" | ")[0]
    
    with col2:
        oc_buscada = st.text_input(
            "Filtrar por N° de Orden de Compra (OC):",
            help="Escriba un número de OC para filtrar los resultados (búsqueda parcial)."
        )

    st.subheader(f"Resultados de la Búsqueda")
    st.markdown("---")

    # --- 3. Filtrar y Mostrar OCs ---
    today = pd.Timestamp.now().floor('D')
    
    # Limpiamos las fechas y cantidades de OC
    df_oc_clean = df_oc.copy()
    try:
        df_oc_clean['Fecha de entrega de la línea'] = pd.to_datetime(df_oc_clean['Fecha de entrega de la línea'], format='%Y-m-%d', errors='coerce')
        df_oc_clean['Cantidad'] = pd.to_numeric(df_oc_clean['Cantidad'], errors='coerce')
    except Exception as e:
        st.error(f"Error procesando datos de OC: {e}")
        st.stop()

    # --- AÑADE ESTA LÍNEA AQUÍ ---
    # Convertimos la OC a string para permitir la búsqueda parcial
    df_oc_clean['Número de documento'] = df_oc_clean['Número de documento'].astype(str)
    # -------------------------------

    # Empezamos con el filtro base (futuras y con cantidad)
    df_llegadas_detalle = df_oc_clean[
        (df_oc_clean['Cantidad'] > 0) & 
        (df_oc_clean['Fecha de entrega de la línea'] >= today)  
    ].copy() # Hacemos una copia para evitar SettingWithCopyWarning

    # Aplicamos el filtro de SKU si no es "Todas"
    if sku_seleccionado != "Todas":
        df_llegadas_detalle = df_llegadas_detalle[
            df_llegadas_detalle['Número de artículo'] == sku_seleccionado
        ]

    # Aplicamos el filtro de OC si se escribió algo
    if oc_buscada:
        df_llegadas_detalle = df_llegadas_detalle[
            df_llegadas_detalle['Número de documento'].str.contains(
                oc_buscada, 
                case=False, # Ignora mayúsculas/minúsculas
                na=False    # Trata los NaN como si no coincidieran
            )
        ]
    
    # ----- FIN DE LA MODIFICACIÓN -----

    # --- 4. Mostrar DataFrame ---
    if df_llegadas_detalle.empty:
        st.info("No se encontraron llegadas programadas que coincidan con los filtros.")
    else:
        # Validamos que las columnas existan
        if 'Comentarios' not in df_llegadas_detalle.columns:
             df_llegadas_detalle['Comentarios'] = 'N/A' 
                 
        if 'Número de documento' not in df_llegadas_detalle.columns:
             st.error("Columna 'Número de documento' (OC) no encontrada en OPOR.xlsx")
             st.stop()

        # Seleccionamos las columnas de interés
        df_display = df_llegadas_detalle[[
            'Fecha de entrega de la línea',
            'Número de documento',
            'Número de artículo',
            'Cantidad',
            'Comentarios'
        ]].copy()
        
        # Agregamos el nombre del artículo usando el mapa
        df_display['Nombre Artículo'] = df_display['Número de artículo'].map(mapa_nombres).fillna('Nombre no encontrado')
        
        # Reordenamos y Renombramos
        df_display = df_display[[
            'Fecha de entrega de la línea',
            'Número de documento',
            'Número de artículo',
            'Nombre Artículo',
            'Cantidad',
            'Comentarios'
        ]]
        
        df_display.rename(columns={
            'Fecha de entrega de la línea': 'Fecha Llegada',
            'Número de documento': 'N° Orden Compra',
            'Número de artículo': 'SKU',
            'Nombre Artículo': 'Producto',
            'Cantidad': 'Cantidad',
            'Comentarios': 'Comentarios'
        }, inplace=True)
        
        df_display = df_display.sort_values(by='Fecha Llegada')

        # Formateamos para mejor lectura
        df_display['Fecha Llegada'] = df_display['Fecha Llegada'].dt.strftime('%Y-%m-%d')
        df_display['Cantidad'] = df_display['Cantidad'].apply(lambda x: f"{x:,.0f}")

        st.dataframe(df_display, use_container_width=True, hide_index=True)
# ---------------------------------------------------------------------
# --- PUNTO DE ENTRADA PRINCIPAL (MAIN) ---
# ---------------------------------------------------------------------
def main():
    """
    Función principal que enruta a la página correcta.
    """
    
    # --- 1. Configuración de la Página (Debe ser lo primero) ---
    st.set_page_config(
        layout="wide",
        page_title="ABASTECIMIENTO SUPREMO", # <--- Título de la pestaña
        page_icon="COPEC-FLUX.svg"  # <--- Ícono de la pestaña (puedes usar un emoji)
    )

    # --- 2. Inicialización del Estado de Página ---
    if 'page' not in st.session_state:
        st.session_state.page = 'menu'

    # --- 3. Enrutamiento de Página (Page Routing) ---
    if st.session_state.page == 'simulator':
        show_simulator()
    elif st.session_state.page == 'arrivals':
        show_arrivals_page() 
    elif st.session_state.page == 'menu':
        show_main_menu()
    else:
        st.session_state.page = 'menu'
        show_main_menu()



# --- Punto de Entrada de Ejecución ---
if __name__ == "__main__":
    main()
