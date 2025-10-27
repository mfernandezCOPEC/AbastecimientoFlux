# --- ARCHIVO: appv3.py ---
# (Guarda este archivo como app.py y ejecútalo con: streamlit run app.py)

import streamlit as st
import pandas as pd
import config         # Importa constantes
import data_loader    # Importa la carga de datos
import simulator      # Importa el motor de simulación
import ui_helpers     # Importa las funciones de gráficos y métricas

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
    # Manejamos el error de "Archivo no encontrado" aquí
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
        value="95%"
    )
    service_level_z = config.Z_SCORE_MAP[service_level_str]
    
    # --- CORRECCIÓN: Variable renombrada a lead_time_days ---
    lead_time_days = st.sidebar.number_input("5. Lead Time (Días):", min_value=1, max_value=120, value=90)
    
    dias_a_simular = st.sidebar.number_input("6. Días a Simular:", min_value=30, max_value=365, value=90)
    
    
    # --- 4. Disparador de Ejecución ---
    if st.sidebar.button("🚀 Ejecutar Simulación", type="primary"):
        with st.spinner("Calculando simulación..."):
            
            # --- A. Ejecutar Simulación ---
            # ----- INICIO DE LA CORRECCIÓN -----
            # Ahora recibimos 4 valores, no 3
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
            # ----- FIN DE LA CORRECCIÓN -----
            
            # --- B. Mostrar Métricas ---
            st.subheader(f"Resultados para: {sku_seleccionado}")
            st.caption(f"Nombre: {mapa_nombres.get(sku_seleccionado, 'N/A')}")
            ui_helpers.display_metrics(metrics, lead_time_days, service_level_z)
            
            # --- C. NUEVO: Mostrar Recomendación de Pedido ---
            st.markdown("---") # Separador
            ui_helpers.display_order_recommendation(metrics, llegadas_map)
            # --- FIN DE LA NUEVA SECCIÓN ---
            
            # --- D. NUEVO: Mostrar Detalle de Llegadas ---
            # (Agregamos esta sección que faltaba en la versión del menú)
            st.markdown("---") # Separador
            ui_helpers.display_arrival_details(df_llegadas_detalle)
            # --- FIN DE LA NUEVA SECCIÓN ---

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
            st.pyplot(fig)
            
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
    st.title("Menú Principal de Abastecimiento")
    st.markdown("Seleccione la herramienta que desea utilizar:")
    
    st.write("") # Espacio
    
    # Botón para ir al simulador
    if st.button("📈 Simulador de Proyección de Inventario", type="primary"):
        st.session_state.page = 'simulator'
        st.rerun() # Forzar la recarga de la app para cambiar de página

    # --- PRÓXIMAMENTE ---
    # Aquí puedes agregar más botones en el futuro
    st.write("") # Espacio
    st.button("📊 Dashboard de Ventas (Próximamente)", disabled=True)
    st.button("⚙️ Configuración (Próximamente)", disabled=True)

# ---------------------------------------------------------------------
# --- PUNTO DE ENTRADA PRINCIPAL (MAIN) ---
# ---------------------------------------------------------------------
def main():
    """
    Función principal que enruta a la página correcta.
    """
    
    # --- 1. Configuración de la Página (Debe ser lo primero) ---
    st.set_page_config(layout="wide")

    # --- 2. Inicialización del Estado de Página ---
    # Si 'page' no existe en el estado de la sesión, lo inicializamos en 'menu'
    if 'page' not in st.session_state:
        st.session_state.page = 'menu'

    # --- 3. Enrutamiento de Página (Page Routing) ---
    # Cargar la página correspondiente según el estado
    if st.session_state.page == 'simulator':
        show_simulator()
    elif st.session_state.page == 'menu':
        show_main_menu()
    else:
        # Por si acaso, volver al menú si el estado es inválido
        st.session_state.page = 'menu'
        show_main_menu()

# --- Punto de Entrada de Ejecución ---
if __name__ == "__main__":
    main()
