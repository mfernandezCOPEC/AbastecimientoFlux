# --- ARCHIVO: src/analysis.py ---
# (NUEVO ARCHIVO para la lógica de negocio separada)

def calculate_order_recommendation(metrics, llegadas_map):
    """
    Calcula la lógica de recomendación de pedido (cuánto pedir).
    Retorna un diccionario con los cálculos y la decisión.
    """
    
    # --- 1. Obtener Métricas Clave ---
    initial_stock = metrics['initial_stock']
    on_order_stock = sum(llegadas_map.values())
    rop = metrics['reorder_point']
    safety_stock = metrics['safety_stock']
    avg_monthly_demand = metrics['monthly_demand_mean']

    # --- 2. Calcular Política de Inventario (s, S) ---
    
    # 's' = ROP
    
    # 'S' = Nivel Objetivo (Order-Up-To Level)
    target_stock_level = safety_stock + avg_monthly_demand
    
    # Posición de Inventario = Stock Físico + Stock en Tránsito
    inventory_position = initial_stock + on_order_stock
    
    # --- 3. Generar Recomendación ---
    suggested_order_qty = 0.0
    is_below_rop = inventory_position <= rop
    status = "info" # Puede ser 'info', 'success', 'warning'

    if is_below_rop:
        # Estamos en o por debajo del punto de reorden. Hay que pedir.
        suggested_order_qty = target_stock_level - inventory_position
        suggested_order_qty = max(0.0, suggested_order_qty) 
        
        if suggested_order_qty > 0:
            status = "success"
        else:
            status = "warning"
    else:
        status = "info"
        
    # --- 4. Retornar los resultados ---
    return {
        "inventory_position": inventory_position,
        "rop": rop,
        "target_stock_level": target_stock_level,
        "suggested_order_qty": suggested_order_qty,
        "is_below_rop": is_below_rop,
        "status": status
    }