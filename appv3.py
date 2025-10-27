# --- ARCHIVO: app.py ---
# (Guarda este archivo como app.py)
# 
# Para ejecutar la aplicación, abre tu terminal y escribe:
# streamlit run app.py

import streamlit as st
import pandas as pd
import numpy as np
import config       # Importa tu archivo de configuración
import simulator    # Importa la lógica de tu simulador

# --- 1. CONFIGURACIÓN DE LA PÁGINA Y ESTADO DE SESIÓN ---

# Configura el layout de la página para que sea ancho
st.set_page_config(layout="wide", page_title="Gestión de Inventario")

# Inicializa el 'estado de sesión' para saber en qué página estamos.
# Si no existe 'page', la definimos como 'inicio'.
if 'page' not in st.session_state:
    st.session_state.page = 'inicio'

# --- 2. FUNCIONES PARA CAMBIAR DE PÁGINA ---

# Estas funciones se llamarán cuando se presionen los botones del menú.
# Simplemente cambian el valor de 'page' en el estado de la sesión.

def go_to_home():
    """Navega a la página de inicio."""
    st.session_state.page = 'inicio'

def go_to_simulator():
    """Navega a la página del simulador."""
    st.session_state.page = 'simulador'
    
# (Aquí puedes agregar más funciones para futuras páginas)
# def go_to_otra_pagina():
#     st.session_state.page = 'otra_pagina'

# --- 3. DIBUJAR EL MENÚ EN LA BARRA LATERAL (SIDEBAR) ---

st.sidebar.title("Menú de Navegación")
st.sidebar.markdown("---")

# Creamos los botones del menú. 
# on_click llama a la función correspondiente para cambiar de página.
st.sidebar.button("🏠 Inicio", on_click=go_to_home, use_container_width=True)
st.sidebar.button("🚀 SIMULADOR", on_click=go_to_simulator, use_container_width=True)

# (Aquí puedes agregar los nuevos botones que quieras en el futuro)
# st.sidebar.button("📊 Dashboard", on_click=go_to_otra_pagina, use_container_width=True)

# --- 4. FUNCIONES QUE DIBUJAN CADA PÁGINA ---

def show_home_page():
    """Muestra el contenido de la página de Inicio."""
    st.title("Bienvenido al Sistema de Gestión de Inventario 📈")
    st.markdown("---")
    st.header("Herramientas Disponibles:")
    st.subheader("🚀 Simulador de Inventario")
    st.write("Proyecta el comportamiento de tu inventario, calcula el Stock de Seguridad y el Punto de Reorden basado en datos históricos.")
    st.write("---")
    st.info("Selecciona 'SIMULADOR' en el menú de la izquierda para comenzar.")

def show_simulator_page():
    """Muestra el contenido de la página del Simulador (tu app actual)."""
    
    st.title("🚀 Simulador de Inventario")
    st.write("Esta herramienta utiliza datos históricos de consumo y órdenes de compra para simular el inventario futuro y calcular métricas clave.")
    st.markdown("---")
    
    # --- Aquí va toda la interfaz de tu aplicación actual ---
    # (He creado una interfaz de ejemplo basada en tu función)

    st.header("1. Carga de Archivos")
    st.info("Carga los 3 archivos CSV con los datos de Stock, Consumo y Órdenes de Compra (OC).")
    
    col_files_1, col_files_2, col_files_3 = st.columns(3)
    with col_files_1:
        uploaded_stock = st.file_uploader("Cargar DF Stock (df_stock_raw)", type=["csv", "xlsx"])
    with col_files_2:
        uploaded_consumo = st.file_uploader("Cargar DF Consumo (df_consumo_raw)", type=["csv", "xlsx"])
    with col_files_3:
        uploaded_oc = st.file_uploader("Cargar DF Órdenes de Compra (df_oc_raw)", type=["csv", "xlsx"])

    st.markdown("---")
    st.header("2. Parámetros de Simulación")

    col_params_1, col_params_2, col_params_3 = st.columns(3)
    with col_params_1:
        st.subheader("Identificación")
        sku_to_simulate = st.text_input("SKU a Simular", "SKU-EJEMPLO-001")
        warehouse_code = st.text_input("Código de Bodega (Stock)", "BF0001")
        consumption_warehouse = st.text_input("Bodega de Consumo", "BC0001")
        
    with col_params_2:
        st.subheader("Parámetros de Tiempo")
        simulation_days = st.number_input("Días a Simular", min_value=90, max_value=730, value=365)
        lead_time_days = st.number_input("Lead Time (días)", min_value=1, max_value=120, value=30)
        
    with col_params_3:
        st.subheader("Nivel de Servicio")
        # Z-Score para 95% de Nivel de Servicio
        service_level_z = st.slider("Nivel de Servicio (Z-Score)", 
                                    min_value=1.0, max_value=3.0, 
                                    value=1.65, step=0.01)
        st.caption(f"Valor 1.65 equivale a ~95% N.S.")

    st.markdown("---")
    
    # Botón para ejecutar la simulación
    if st.button("▶️ Ejecutar Simulación", use_container_width=True, type="primary"):
        if uploaded_stock and uploaded_consumo and uploaded_oc:
            
            # Cargar los datos (Implementación de ejemplo, ajusta según tu formato)
            try:
                df_stock_raw = pd.read_csv(uploaded_stock) if uploaded_stock.name.endswith('csv') else pd.read_excel(uploaded_stock)
                df_consumo_raw = pd.read_csv(uploaded_consumo) if uploaded_consumo.name.endswith('csv') else pd.read_excel(uploaded_consumo)
                df_oc_raw = pd.read_csv(uploaded_oc) if uploaded_oc.name.endswith('csv') else pd.read_excel(uploaded_oc)
                
                with st.spinner("Procesando datos y ejecutando simulación... Por favor espera."):
                    # Llamamos a la función de lógica desde simulator.py
                    df_sim, metrics, llegadas_map = simulator.run_inventory_simulation(
                        sku_to_simulate=sku_to_simulate,
                        warehouse_code=warehouse_code,
                        consumption_warehouse=consumption_warehouse,
                        df_stock_raw=df_stock_raw,
                        df_consumo_raw=df_consumo_raw,
                        df_oc_raw=df_oc_raw,
                        simulation_days=simulation_days,
                        lead_time_days=lead_time_days,
                        service_level_z=service_level_z
                    )
                
                st.success("¡Simulación completada con éxito!")
                st.balloons()
                
                # --- Mostrar Resultados ---
                st.header("Resultados de la Simulación")
                
                st.subheader("Métricas Clave Calculadas")
                col_metrics_1, col_metrics_2, col_metrics_3 = st.columns(3)
                col_metrics_1.metric("Stock de Seguridad (SS)", f"{metrics['safety_stock']:.2f} un.")
                col_metrics_2.metric("Punto de Reorden (ROP)", f"{metrics['reorder_point']:.2f} un.")
                col_metrics_3.metric("Stock Inicial", f"{metrics['initial_stock']:.2f} un.")
                
                st.subheader("Gráfico de Proyección de Inventario")
                st.line_chart(df_sim['NivelInventario'])
                
                st.subheader("Detalle de Métricas")
                st.json(metrics) # Muestra todas las métricas en formato JSON

            except Exception as e:
                st.error(f"Ocurrió un error durante la simulación: {e}")
                st.exception(e)
        else:
            st.warning("⚠️ Por favor, carga los 3 archivos de datos para poder ejecutar la simulación.")

# --- 5. LÓGICA PRINCIPAL PARA MOSTRAR LA PÁGINA CORRECTA ---

# Este es el "enrutador" principal.
# Revisa el valor de 'st.session_state.page' y llama a la función
# que dibuja la página correspondiente.

if st.session_state.page == 'inicio':
    show_home_page()
elif st.session_state.page == 'simulador':
    show_simulator_page()
# (Aquí puedes agregar los 'elif' para tus futuras páginas)
# elif st.session_state.page == 'otra_pagina':
#     show_otra_pagina()
