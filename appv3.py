# --- ARCHIVO: app.py ---
# (Esta es tu página principal / Menú)

import streamlit as st
import sys
from pathlib import Path

# --- 1. Configuración de la Página y del Path ---
# Añade el directorio 'src' al path de Python para poder importar los módulos
# NOTA: Esto es crucial para que los imports de 'src' funcionen
src_path = str(Path(__file__).parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

import data_loader # Importa desde 'src'

# --- 2. Configuración de la Página (Debe ser lo primero) ---
st.set_page_config(
    layout="wide",
    page_title="Menú Abastecimiento", # <--- Título de la pestaña
    page_icon="assets/COPEC-FLUX.svg"  # <--- Ruta actualizada al ícono
)

# --- 3. Carga de Datos en Session State ---
# Llama a la función que carga y guarda los datos en st.session_state
# Esto se ejecutará una vez y estará disponible para todas las páginas.
data_loader.load_data_into_session()

# --- 4. Lógica de la Página del Menú Principal ---

# --- MOSTRAR IMAGEN DE PORTADA ---
try:
    # Ruta actualizada a la imagen
    col1, col_img, col3 = st.columns([1, 2, 1])
    with col_img: 
        st.image("assets/COPEC-FLUX.svg", use_container_width=True)
except FileNotFoundError:
    st.warning("No se encontró el archivo 'COPEC-FLUX.svg'. Asegúrate de agregarlo a la carpeta 'assets/'.")
except Exception as e:
    st.error(f"No se pudo cargar la imagen: {e}")

st.title("Menú Principal de Abastecimiento")
st.markdown("Seleccione la herramienta que desea utilizar en el menú de la izquierda.")

st.info(
    """
    **Bienvenido al Asistente de Abastecimiento.**

    - **📈 Simulador:** Proyecta tu inventario futuro, calcula el Stock de Seguridad (SS) y el Punto de Reorden (ROP), y recibe recomendaciones de pedido.
    - **📦 Llegadas:** Consulta el estado y las fechas de tus Órdenes de Compra (OC) programadas.
    """
)

# --- PRÓXIMAMENTE ---
st.write("") # Espacio
st.subheader("Próximamente")
col1, col2 = st.columns(2)
col1.button("📊 Dashboard de Ventas", disabled=True, use_container_width=True)
col2.button("⚙️ Configuración", disabled=True, use_container_width=True)

# Limpia la barra lateral (opcional)
st.sidebar.markdown("---")
st.sidebar.info("Seleccione una página arriba para comenzar.")