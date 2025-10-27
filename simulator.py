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
    
    # Define la fecha de 'hoy' (inicio de la simulación)
    today = pd.Timestamp.now().floor('D')
    
    # --- B. CÁLCULO DE STOCK INICIAL (I_0) ---
    
    # Filtra el DataFrame de stock para el SKU y bodega específicos
    df_stock_filtered = df_stock_raw[
        (df_stock_raw['CodigoArticulo'] == sku_to_simulate) &
        (df_stock_raw['CodigoBodega'] == warehouse_code)
    ].copy()
    
    # Asegura que el stock sea numérico y calcula el total
    df_stock_filtered['DisponibleParaPrometer'] = pd.to_numeric(df_stock_filtered['DisponibleParaPrometer'], errors='coerce')
    initial_stock = df_stock_filtered['DisponibleParaPrometer'].sum()

    # --- C. CÁLCULO DE CONSUMO ---
    
    # Filtra el DataFrame de consumo para el SKU y bodega de consumo específicos
    df_consumo_filtered = df_consumo_raw[
        (df_consumo_raw['CodigoArticulo'] == sku_to_simulate) &
        (df_consumo_raw['BodegaDestino_Requerida'] == consumption_warehouse)
    ].copy()
    
    # Inicializa métricas de demanda (buena práctica para asegurar que existan)
    daily_demand_mean = 0.0
    daily_demand_std = 0.0
    monthly_demand_mean = 0.0
    demand_M_0, demand_M_1, demand_M_2, demand_M_3 = 0.0, 0.0, 0.0, 0.0

    # Define las fechas de inicio para los meses a analizar (M, M-1, M-2, M-3)
    start_of_current_month = today.replace(day=1)
    start_of_M_minus_1 = start_of_current_month - pd.DateOffset(months=1)
    start_of_M_minus_2 = start_of_current_month - pd.DateOffset(months=2)
    start_of_M_minus_3 = start_of_current_month - pd.DateOffset(months=3)
    
    # Solo procesa si hay historial de consumo
    if not df_consumo_filtered.empty:
        
        # 1. Preparación de datos de consumo
        
        # Asegura que la cantidad sea numérica (ignora errores de formato)
        df_consumo_filtered['CantidadSolicitada'] = pd.to_numeric(df_consumo_filtered['CantidadSolicitada'], errors='coerce')
        
        # Establece la fecha como índice para poder re-muestrear (resample)
        df_consumo_indexed = df_consumo_filtered.set_index('FechaSolicitud')
        
        # Agrupa el consumo por mes ('MS' = Month Start) y suma las cantidades
        consumo_mensual = df_consumo_indexed.resample('MS')['CantidadSolicitada'].sum()
        
        # 2. Cálculo para SS y ROP (promedios históricos)
        
        # --- MODIFICACIÓN CLAVE ---
        # Excluimos el mes actual de los cálculos estadísticos (media, std)
        # ya que es un mes incompleto y "ensuciaría" el promedio histórico.
        consumo_historico_completo = consumo_mensual[consumo_mensual.index < start_of_current_month]
        # --- FIN DE LA MODIFICACIÓN ---

        if len(consumo_historico_completo) > 1:
            # Calcula la media y std usando SOLO los meses históricos completos
            monthly_demand_mean = consumo_historico_completo.mean()
            monthly_demand_std = consumo_historico_completo.std()
            
            # Convierte las métricas mensuales a diarias
            daily_demand_mean = monthly_demand_mean / config.AVERAGE_DAYS_PER_MONTH
            daily_demand_std = monthly_demand_std / np.sqrt(config.AVERAGE_DAYS_PER_MONTH) 
            
        elif len(consumo_historico_completo) == 1:
            # Si solo hay 1 mes histórico (ej. estamos en el 2do mes de data)
            monthly_demand_mean = consumo_historico_completo.mean()
            daily_demand_mean = monthly_demand_mean / config.AVERAGE_DAYS_PER_MONTH
            # daily_demand_std se mantiene en 0.0 (inicializado)

        # 3. Cálculo para Req. 1 (meses individuales)
        
        # Aquí SÍ usamos 'consumo_mensual' (el original) porque queremos
        # obtener el valor del mes actual (M_0), aunque esté incompleto.
        demand_M_0 = consumo_mensual.get(start_of_current_month, 0)
        demand_M_1 = consumo_mensual.get(start_of_M_minus_1, 0)
        demand_M_2 = consumo_mensual.get(start_of_M_minus_2, 0)
        demand_M_3 = consumo_mensual.get(start_of_M_minus_3, 0)

    # --- D. CÁLCULO DE SS y ROP ---
    
    # Demanda esperada durante el tiempo de entrega (Lead Time)
    demand_during_lead_time = daily_demand_mean * lead_time_days
    
    # Variabilidad (Std Dev) durante el tiempo de entrega
    std_dev_during_lead_time = daily_demand_std * np.sqrt(lead_time_days)
    
    # Stock de Seguridad (Safety Stock)
    safety_stock = service_level_z * std_dev_during_lead_time
    
    # Punto de Reorden (Reorder Point)
    reorder_point = demand_during_lead_time + safety_stock

    # --- E. CÁLCULO DE LLEGADAS (OC) ---
    
    df_oc_clean = df_oc_raw.copy()
    try:
        # Limpieza de fechas y cantidades de Órdenes de Compra
        df_oc_clean['Fecha de entrega de la línea'] = pd.to_datetime(df_oc_clean['Fecha de entrega de la línea'], format='%Y-m-%d', errors='coerce')
        df_oc_clean['Cantidad'] = pd.to_numeric(df_oc_clean['Cantidad'], errors='coerce')
    except Exception as e:
        print(f"Error limpiando df_oc: {e}.") # Manejo básico de errores

    # Filtra OC relevantes: mismo SKU, cantidad positiva, y fecha futura
# --- E. CÁLCULO DE LLEGADAS (OC) ---
# ... (código de limpieza de df_oc_clean) ...

    # CAMBIA 'df_oc_filtered' POR 'df_llegadas_detalle'
    df_llegadas_detalle = df_oc_clean[
        (df_oc_clean['Número de artículo'] == sku_to_simulate) &
        (df_oc_clean['Cantidad'] > 0) & 
        (df_oc_clean['Fecha de entrega de la línea'] >= today)
    ]
    
    # Usa la nueva variable para calcular el mapa
    llegadas_por_fecha = df_llegadas_detalle.groupby('Fecha de entrega de la línea')['Cantidad'].sum() 
    llegadas_map = llegadas_por_fecha.to_dict()
    
    # --- F. EJECUTAR SIMULACIÓN DÍA A DÍA ---
    
    inventory_level = initial_stock
    history_list = [] # Lista para guardar el nivel de inventario de cada día
    date_list = []    # Lista para guardar la fecha de cada día

    for day in range(simulation_days):
        current_date = today + pd.Timedelta(days=day)
        
        # 1. Guardar el inventario ANTES de cualquier transacción del día
        history_list.append(inventory_level)
        date_list.append(current_date)
        
        # 2. Recibir llegadas de OC programadas para 'current_date'
        # .get(current_date, 0) busca la fecha; si no la encuentra, suma 0
        inventory_level += llegadas_map.get(current_date, 0)
        
        # 3. Simular el consumo (demanda) del día
        if daily_demand_std > 0:
            # Genera un consumo aleatorio basado en la media y std (distribución normal)
            # (Corregido: 'scale' debe ser 'daily_demand_std')
            daily_consumption = np.random.normal(loc=daily_demand_mean, scale=0) #, scale=daily_demand_std)
        else:
            # Si no hay std (datos insuficientes), usa la media como consumo determinístico
            daily_consumption = daily_demand_mean
            
        # Asegura que el consumo no sea negativo
        daily_consumption = max(0, daily_consumption)
        
        # 4. Restar el consumo del inventario
        inventory_level -= daily_consumption
        
        # 5. Asegurar que el inventario no sea negativo (no se puede tener stock < 0)
        inventory_level = max(0, inventory_level)
            
    # Crea el DataFrame final de la simulación
    df_sim = pd.DataFrame({'NivelInventario': history_list}, index=pd.Index(date_list, name='Fecha'))

    # --- G. EMPAQUETAR RESULTADOS ---
    
    # Diccionario con las métricas clave para retornar
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

    return df_sim, metrics, llegadas_map, df_llegadas_detalle

