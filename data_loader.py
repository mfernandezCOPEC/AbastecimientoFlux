# --- ARCHIVO: data_loader.py ---
# (Guarda este archivo como data_loader.py)

import pandas as pd
import streamlit as st
import config # Importamos nuestro archivo de configuración

@st.cache_data
def load_data():
    """
    Carga, limpia y pre-procesa todos los archivos de datos iniciales.
    Maneja errores de carga y aplica filtros globales.
    
    Retorna:
    - tupla(pd.DataFrame): (df_stock, df_oc, df_consumo, df_residencial)
    
    Lanza:
    - FileNotFoundError: Si no se encuentra un archivo Excel esencial.
    """
    print("--- Cargando y Limpiando Datos Globales (Ejecutado 1 Vez) ---")
    
    try:
        df_stock = pd.read_excel('Stock.xlsx')
        df_residencial = pd.read_excel(r"BD residencial\BD_Master_Residencial.xlsx")
        df_oc = pd.read_excel("OPOR.xlsx")
        df_consumo = pd.read_excel('ST_OWTR.xlsx')
        print("Archivos 'Stock', 'OPOR' y 'ST_OWTR' cargados.")
    
    except FileNotFoundError as e:
        # En lugar de usar st.error aquí, lanzamos la excepción
        # para que la app principal (app.py) la maneje.
        print(f"Error: No se pudo encontrar el archivo: {e.filename}.")
        raise e # Esto detendrá la carga y será atrapado por app.py
    except Exception as e:
        st.error(f"Error inesperado al leer archivos: {e}")
        return None, None, None, None

    # --- Limpieza Global de Fechas ---
    df_oc['Fecha de contabilización'] = pd.to_datetime(df_oc['Fecha de contabilización'], format='%Y-m-%d', errors='coerce')
    df_consumo['FechaSolicitud'] = pd.to_datetime(df_consumo['FechaSolicitud'], errors='coerce')
    
    df_oc = df_oc.dropna(subset=['Fecha de contabilización'])
    df_consumo = df_consumo.dropna(subset=['FechaSolicitud'])

    # --- Filtro Global de 4 Meses ---
    hoy = pd.Timestamp.now()
    hace_4_meses = (hoy - pd.DateOffset(months=4)).replace(day=1) 
    
    df_oc = df_oc[df_oc['Fecha de contabilización'] >= hace_4_meses].copy()
    df_consumo = df_consumo[df_consumo['FechaSolicitud'] >= hace_4_meses].copy()

    # --- Limpieza Global de SKUs (Usando config) ---
    df_consumo['CodigoArticulo'] = df_consumo['CodigoArticulo'].replace(config.MAPEO_SKUS)
    # Nota: El mapeo de SKUs en df_oc y df_stock estaba comentado en tu código original.
    # Si lo necesitas, descomenta las siguientes líneas:
    # df_oc['Número de artículo'] = df_oc['Número de artículo'].replace(config.MAPEO_SKUS)
    # df_stock['CodigoArticulo'] = df_stock['CodigoArticulo'].replace(config.MAPEO_SKUS)
    
    print("Datos globales cargados y limpiados.")
    
    return df_stock, df_oc, df_consumo, df_residencial