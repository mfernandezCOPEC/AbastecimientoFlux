# --- ARCHIVO: simulator.py ---
# (Guarda este archivo como simulator.py)

import pandas as pd
import numpy as np
import config # Importamos la constante

def run_inventory_simulation(
    sku_to_simulate: str,
    warehouse_code: str,
    consumption_warehouse: str,
    df_stock_raw: pd.DataFrame,
    df_consumo_raw: pd.DataFrame,
    df_oc_raw: pd.DataFrame,
    simulation_days: int,
    lead_time_days: int, 
    service_level_z: float
):
    """
    Ejecuta la lógica de simulación de inventario día a día.
    
    Retorna:
    - df_sim (pd.DataFrame): DataFrame indexado por fecha con el inventario diario.
    - metrics (dict): Diccionario con todas las métricas calculadas (SS, ROP, demanda, etc.).
    - llegadas_map (dict): Diccionario de {fecha: cantidad} para las llegadas de OC.
    """
    
    today = pd.Timestamp.now().floor('D')
    
    # --- B. CÁLCULO DE STOCK INICIAL (I_0) ---
    df_stock_filtered = df_stock_raw[
        (df_stock_raw['CodigoArticulo'] == sku_to_simulate) &
        (df_stock_raw['CodigoBodega'] == warehouse_code)
    ].copy()
    df_stock_filtered['DisponibleParaPrometer'] = pd.to_numeric(df_stock_filtered['DisponibleParaPrometer'], errors='coerce')
    initial_stock = df_stock_filtered['DisponibleParaPrometer'].sum()

    # --- C. CÁLCULO DE CONSUMO ---
    df_consumo_filtered = df_consumo_raw[
        (df_consumo_raw['CodigoArticulo'] == sku_to_simulate) &
        (df_consumo_raw['BodegaDestino_Requerida'] == consumption_warehouse)
    ].copy()
    
    # Inicializa métricas
    daily_demand_mean = 0.0
    daily_demand_std = 0.0
    monthly_demand_mean = 0.0
    demand_M_0, demand_M_1, demand_M_2, demand_M_3 = 0.0, 0.0, 0.0, 0.0

    # Define fechas para Req. 1
    start_of_current_month = today.replace(day=1)
    start_of_M_minus_1 = start_of_current_month - pd.DateOffset(months=1)
    start_of_M_minus_2 = start_of_current_month - pd.DateOffset(months=2)
    start_of_M_minus_3 = start_of_current_month - pd.DateOffset(months=3)
    
    if not df_consumo_filtered.empty:
        df_consumo_filtered['CantidadSolicitada'] = pd.to_numeric(df_consumo_filtered['CantidadSolicitada'], errors='coerce')
        df_consumo_indexed = df_consumo_filtered.set_index('FechaSolicitud')
        consumo_mensual = df_consumo_indexed.resample('MS')['CantidadSolicitada'].sum()
        
        # 1. Cálculo para SS y ROP (promedio)
        if len(consumo_mensual) > 1:
            monthly_demand_mean = consumo_mensual.mean()
            monthly_demand_std = consumo_mensual.std()
            daily_demand_mean = monthly_demand_mean / config.AVERAGE_DAYS_PER_MONTH
            daily_demand_std = monthly_demand_std / np.sqrt(config.AVERAGE_DAYS_PER_MONTH) 
        elif len(consumo_mensual) == 1:
            monthly_demand_mean = consumo_mensual.mean()
            daily_demand_mean = monthly_demand_mean / config.AVERAGE_DAYS_PER_MONTH

        # 2. Cálculo para Req. 1 (individual)
        demand_M_0 = consumo_mensual.get(start_of_current_month, 0)
        demand_M_1 = consumo_mensual.get(start_of_M_minus_1, 0)
        demand_M_2 = consumo_mensual.get(start_of_M_minus_2, 0)
        demand_M_3 = consumo_mensual.get(start_of_M_minus_3, 0)

    # --- D. CÁLCULO DE SS y ROP ---
    demand_during_lead_time = daily_demand_mean * lead_time_days
    std_dev_during_lead_time = daily_demand_std * np.sqrt(lead_time_days)
    safety_stock = service_level_z * std_dev_during_lead_time
    reorder_point = demand_during_lead_time + safety_stock

    # --- E. CÁLCULO DE LLEGADAS (OC) ---
    df_oc_clean = df_oc_raw.copy()
    try:
        df_oc_clean['Fecha de entrega de la línea'] = pd.to_datetime(df_oc_clean['Fecha de entrega de la línea'], format='%Y-m-%d', errors='coerce')
        df_oc_clean['Cantidad'] = pd.to_numeric(df_oc_clean['Cantidad'], errors='coerce')
    except Exception as e:
        print(f"Error limpiando df_oc: {e}.")

    df_oc_filtered = df_oc_clean[
        (df_oc_clean['Número de artículo'] == sku_to_simulate) &
        (df_oc_clean['Cantidad'] > 0) & 
        (df_oc_clean['Fecha de entrega de la línea'] >= today)
    ]
    llegadas_por_fecha = df_oc_filtered.groupby('Fecha de entrega de la línea')['Cantidad'].sum() 
    llegadas_map = llegadas_por_fecha.to_dict()

    # --- F. EJECUTAR SIMULACIÓN DÍA A DÍA ---
    inventory_level = initial_stock
    history_list = [] 
    date_list = []

    for day in range(simulation_days):
        current_date = today + pd.Timedelta(days=day)
        history_list.append(inventory_level)
        date_list.append(current_date)
        
        inventory_level += llegadas_map.get(current_date, 0)
        
        if daily_demand_std > 0:
            daily_consumption = np.random.normal(loc=daily_demand_mean, scale= 0) #scale=daily_demand_std)
        else:
            daily_consumption = daily_demand_mean
            
        daily_consumption = max(0, daily_consumption)
        inventory_level -= daily_consumption
        inventory_level = max(0, inventory_level)
            
    df_sim = pd.DataFrame({'NivelInventario': history_list}, index=pd.Index(date_list, name='Fecha'))

    # --- G. EMPAQUETAR RESULTADOS ---
    metrics = {
        'initial_stock': initial_stock,
        'monthly_demand_mean': monthly_demand_mean,
        'llegadas_count': len(llegadas_map),
        'safety_stock': safety_stock,
        'reorder_point': reorder_point,
        'demand_M_0': (start_of_current_month.strftime('%B').capitalize(), demand_M_0),
        'demand_M_1': (start_of_M_minus_1.strftime('%B').capitalize(), demand_M_1),
        'demand_M_2': (start_of_M_minus_2.strftime('%B').capitalize(), demand_M_2),
        'demand_M_3': (start_of_M_minus_3.strftime('%B').capitalize(), demand_M_3),
    }
    

    return df_sim, metrics, llegadas_map
