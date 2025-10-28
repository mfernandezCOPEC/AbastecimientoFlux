# --- ARCHIVO: ui_helpers.py ---
# (Guarda este archivo como ui_helpers.py)

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import locale
import config
import altair as alt


def setup_locale():
    """Configura el locale a español para los nombres de los meses."""
    try:
        locale.setlocale(locale.LC_TIME, config.LOCALE_ES)
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, config.LOCALE_ES_FALLBACK)
        except locale.Error:
            print(f"Locale '{config.LOCALE_ES}' o '{config.LOCALE_ES_FALLBACK}' no encontrado.")

def create_sku_options(all_skus, df_stock):
    """
    Crea la lista de opciones para el selector de SKU (Req. 2).
    Formato: "SKU | Nombre"
    
    Retorna:
    - opciones_selector_sku (list): Lista de strings formateados.
    - mapa_nombres (dict): Diccionario {SKU: Nombre}.
    - default_index (int): Índice del SKU por defecto.
    """
    mapa_nombres = df_stock.drop_duplicates(subset=['CodigoArticulo']).set_index('CodigoArticulo')['NombreArticulo'].to_dict()
    
    opciones_selector_sku = []
    for sku in all_skus:
        nombre = mapa_nombres.get(sku, "Nombre no encontrado")
        opciones_selector_sku.append(f"{sku} | {nombre}")
        
    # Buscar el índice del SKU por defecto
    default_sku = 'EXI-009231'
    default_index = 0
    for i, option in enumerate(opciones_selector_sku):
        if option.startswith(default_sku):
            default_index = i
            break
            
    return opciones_selector_sku, mapa_nombres, default_index

def display_metrics(metrics, lead_time_days, service_level_z):
    """Muestra todas las métricas en la app de Streamlit."""
    
    st.subheader("Métricas Clave")
    col1, col2, col3 = st.columns(3)
    col1.metric("Stock Inicial (Disp.)", f"{metrics['initial_stock']:,.0f}")
    col2.metric("Consumo Prom. (Simulación)", f"{metrics['monthly_demand_mean']:,.0f}", 
                help="Promedio mensual de todos los datos de consumo cargados, usado para calcular SS y ROP.")
    col3.metric("Llegadas Programadas", f"{metrics['llegadas_count']}")
    
    st.markdown("---")

    # Requerimiento 1: Consumo histórico
    st.subheader("Consumo Histórico Reciente")
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric(f"Demanda {metrics['demand_M_0'][0]} (Actual)", f"{metrics['demand_M_0'][1]:,.0f}")
    col2.metric(f"Demanda {metrics['demand_M_1'][0]}", f"{metrics['demand_M_1'][1]:,.0f}")
    col3.metric(f"Demanda {metrics['demand_M_2'][0]}", f"{metrics['demand_M_2'][1]:,.0f}")
    col4.metric(f"Demanda {metrics['demand_M_3'][0]}", f"{metrics['demand_M_3'][1]:,.0f}")

    st.markdown("---")
    
    st.subheader("Parámetros de Simulación (Calculados)") 
    col1, col2, col3 = st.columns(3)
    col1.metric("Lead Time (Días)", f"{lead_time_days}", help="Parámetro de entrada.")
    col2.metric("Safety Stock (SS)", f"{metrics['safety_stock']:,.0f}", f"Nivel Servicio {service_level_z}Z")
    col3.metric("Punto de Reorden (ROP)", f"{metrics['reorder_point']:,.0f}")

def generate_simulation_plot(df_sim, metrics, llegadas_map, sku_name, simulation_days):
    """
    Genera un gráfico interactivo de Altair para la proyección de inventario.
    
    Retorna:
    - chart (alt.Chart): El gráfico de Altair.
    """
    
    # 1. Preparar el DataFrame principal (Inventario)
    df_plot = df_sim.reset_index()
    
    # 2. Preparar el DataFrame de llegadas (OCs)
    df_llegadas = pd.DataFrame(list(llegadas_map.items()), columns=['Fecha', 'CantidadLlegada'])
    df_llegadas = pd.merge(df_llegadas, df_plot, on='Fecha', how='left')

    # 3. Gráfico base
    base = alt.Chart(df_plot).encode(
        x=alt.X('Fecha:T', title='Fecha', axis=alt.Axis(format="%Y-%m-%d")),
    )

    # 4. Línea de Inventario (CON TOOLTIP)
    inventory_line = base.mark_line(point=True, interpolate='step-after').encode(
        y=alt.Y('NivelInventario:Q', title='Unidades en Stock'),
        tooltip=[
            alt.Tooltip('Fecha:T', format="%Y-%m-%d"), 
            alt.Tooltip('NivelInventario:Q', title='Stock Proyectado', format=',.0f')
        ]
    ).properties(
        title=f'Proyección de Inventario para {sku_name} ({simulation_days} días)'
    )

    # 5. Puntos de Llegada (OCs)
    arrival_points = alt.Chart(df_llegadas).mark_circle(color='green', size=100, opacity=0.8).encode(
        x=alt.X('Fecha:T'),
        y=alt.Y('NivelInventario:Q'),
        tooltip=[
            alt.Tooltip('Fecha:T', title='Llegada de OC', format="%Y-%m-%d"),
            alt.Tooltip('CantidadLlegada:Q', title='Cantidad Recibida', format=',.0f')
        ]
    )

    # 6. Líneas de referencia (ROP y SS)
    # ----- INICIO DE LA CORRECCIÓN -----
    # Usamos alt.value() para asignar un valor constante al tooltip
    rop_line = alt.Chart(pd.DataFrame({'y': [metrics['reorder_point']]})).mark_rule(
        color='blue', strokeDash=[5, 5]
    ).encode(
        y='y',
        tooltip=alt.value(f"Punto de Reorden (ROP): {metrics['reorder_point']:,.0f}")
    )
    
    ss_line = alt.Chart(pd.DataFrame({'y': [metrics['safety_stock']]})).mark_rule(
        color='purple', strokeDash=[5, 5]
    ).encode(
        y='y',
        tooltip=alt.value(f"Safety Stock (SS): {metrics['safety_stock']:,.0f}")
    )
    # ----- FIN DE LA CORRECCIÓN -----

    # 7. Línea de Cero
    zero_line = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(
        color='red', strokeDash=[2, 2]
    ).encode(y='y')

    # 8. Combinar todas las capas y hacerlo interactivo
    final_chart = (inventory_line + arrival_points + rop_line + ss_line + zero_line).interactive()
    
    return final_chart

def prepare_end_of_month_table(df_sim):
    """
    Toma el DataFrame de simulación diaria y lo resume a fin de mes (Req. 3).
    
    Retorna:
    - pd.DataFrame: DataFrame formateado para mostrar en st.dataframe.
    """
    df_fin_de_mes = df_sim['NivelInventario'].resample('M').last().reset_index()
    
    df_fin_de_mes['Mes'] = df_fin_de_mes['Fecha'].dt.strftime('%Y-%m (%B)')
    df_fin_de_mes['Stock al Cierre'] = df_fin_de_mes['NivelInventario'].apply(lambda x: f"{x:,.0f}")
    
    return df_fin_de_mes[['Mes', 'Stock al Cierre']]

# --- NUEVA FUNCIÓN ---
def display_order_recommendation(metrics, llegadas_map):
    """
    Calcula y muestra la recomendación de pedido (cuánto pedir).
    """
    
    # --- 1. Obtener Métricas Clave ---
    initial_stock = metrics['initial_stock']
    on_order_stock = sum(llegadas_map.values())
    rop = metrics['reorder_point']
    safety_stock = metrics['safety_stock']
    avg_monthly_demand = metrics['monthly_demand_mean']

    # --- 2. Calcular Política de Inventario (s, S) ---
    
    # 's' = ROP (ya lo tenemos)
    
    # 'S' = Nivel Objetivo (Order-Up-To Level)
    # Lo definimos como: Safety Stock + Demanda de 1 Mes
    # Si la demanda es 0, el objetivo es solo el Safety Stock (si este es > 0)
    target_stock_level = safety_stock + avg_monthly_demand
    
    # Posición de Inventario = Stock Físico + Stock en Tránsito
    inventory_position = initial_stock + on_order_stock
    
    # --- 3. Generar Recomendación ---
    suggested_order_qty = 0
    is_below_rop = inventory_position <= rop

    if is_below_rop:
        # Estamos en o por debajo del punto de reorden. Hay que pedir.
        # Pedimos la cantidad necesaria para volver al nivel objetivo 'S'.
        suggested_order_qty = target_stock_level - inventory_position
        # Aseguramos no pedir cantidades negativas si estamos sobre-stockeados
        suggested_order_qty = max(0, suggested_order_qty) 

    # --- 4. Mostrar en la UI ---
    st.subheader("Recomendación de Abastecimiento 💡")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Posición de Inventario", f"{inventory_position:,.0f}", 
                help="Stock Inicial (Físico) + Stock en Tránsito (OCs Programadas)")
    
    col2.metric("Punto de Reorden (ROP)", f"{rop:,.0f}", 
                help="Si la 'Posición de Inventario' cae bajo este número, se debe pedir.")
    
    col3.metric("Nivel Objetivo (S)", f"{target_stock_level:,.0f}", 
                help="El nivel de stock al que se desea llegar (SS + 1 Mes Demanda Prom.)")

    # Mostrar el veredicto final
    if is_below_rop and suggested_order_qty > 0:
        st.success(f"**Recomendación:** Pedir **{suggested_order_qty:,.0f} unidades** ahora para reabastecer al Nivel Objetivo.")
    elif is_below_rop and suggested_order_qty == 0:
        st.warning(f"**Alerta:** La posición de inventario ({inventory_position:,.0f}) está por debajo del ROP, pero ya supera el Nivel Objetivo. No se sugiere un nuevo pedido.")
    else:

        st.info(f"**No se necesita pedido.** La posición de inventario ({inventory_position:,.0f}) está por encima del Punto de Reorden ({rop:,.0f}).")


# --- NUEVA FUNCIÓN ---
def display_arrival_details(df_llegadas_detalle):
    """
    Muestra una tabla con el detalle de las próximas llegadas (OCs).
    """
    st.subheader("Detalle de Próximas Llegadas (OC)")
    
    # Asumimos que la columna de OC se llama 'Número de documento'.
    # Si se llama de otra forma en tu Excel 'OPOR.xlsx', 
    # tendrías que cambiar el string 'Número de documento' aquí.
    columna_oc = 'Número de documento' 
    
    if columna_oc not in df_llegadas_detalle.columns:
        st.error(f"Error: La columna '{columna_oc}' no se encontró en el archivo OPOR.")
        st.info("No se puede mostrar el detalle de OCs. Verifica el nombre de la columna en 'ui_helpers.py'.")
        return

    if df_llegadas_detalle.empty:
        st.info("No hay órdenes de compra programadas para este SKU.")
    else:
        # Seleccionamos, renombramos y ordenamos las columnas para mostrar
        df_display = df_llegadas_detalle[[
            'Fecha de entrega de la línea', 
            columna_oc, 
            'Cantidad'
        ]].copy()
        
        df_display.rename(columns={
            'Fecha de entrega de la línea': 'Fecha Llegada',
            columna_oc: 'N° Orden Compra',
            'Cantidad': 'Cantidad'
        }, inplace=True)
        
        df_display = df_display.sort_values(by='Fecha Llegada')
        
        # Formatear para mejor visualización
        df_display['Fecha Llegada'] = df_display['Fecha Llegada'].dt.strftime('%Y-%m-%d')
        df_display['Cantidad'] = df_display['Cantidad'].apply(lambda x: f"{x:,.0f}")
        
        # Mostramos la tabla
        st.dataframe(df_display, use_container_width=True, hide_index=True)


