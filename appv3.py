# --- ARCHIVO: app.py ---
# (Esta es tu página principal / Menú)
import streamlit as st
import sys
from pathlib import Path

# --- 1. Configuración de la Página y del Path ---
src_path = str(Path(__file__).parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

import data_loader 

# --- 2. Configuración de la Página (Debe ser lo primero) ---
st.set_page_config(
    layout="wide",
    page_title="Menú Abastecimiento", 
    page_icon="assets/COPEC-FLUX.svg"
)

# --- 3. Carga de Datos en Session State ---
data_loader.load_data_into_session()

# --- 4. Lógica de la Página del Menú Principal ---

# --- Encabezado Profesional (Logo + Título) --- (Novedad)
col1, col2 = st.columns([1, 4]) # 1 parte para el logo, 4 para el texto
with col1:
    try:
        st.image("assets/COPEC-FLUX.svg", width=150) # Ajusta el ancho según necesites
    except Exception as e:
        st.error(f"No se pudo cargar logo: {e}")

with col2:
    st.title("Asistente de Abastecimiento Flux")
    st.caption("Bienvenido al portal de simulación y consulta de inventario.")

st.markdown("---") # Separador visual

# --- Mensaje de Bienvenida --- (Novedad)
st.markdown(
    """
    Bienvenido al Asistente de Abastecimiento. Esta plataforma centraliza las herramientas 
    clave para la gestión de inventario.
    
    Seleccione la herramienta que desea utilizar en el menú de la izquierda.
    """
)

st.header("Herramientas Disponibles")

# --- Tarjetas de Navegación (Novedad: Reemplaza st.info) ---
col1, col2 = st.columns(2)

with col1:
    with st.container(border=True): # <-- 'border=True' crea la tarjeta
        st.subheader("📈 Simulador de Inventario")
        st.markdown(
            """
            Proyecte su inventario futuro, calcule el Stock de Seguridad (SS) 
            y el Punto de Reorden (ROP), y reciba recomendaciones de pedido.
            """
        )
        st.info("Seleccione **'Simulador'** en el menú lateral para comenzar.")

with col2:
    with st.container(border=True):
        st.subheader("📦 Consulta de Llegadas")
        st.markdown(
            """
            Consulte el estado y las fechas de sus Órdenes de Compra (OC) 
            programadas, filtrando por SKU o número de documento.
            """
        )
        st.info("Seleccione **'Llegadas'** en el menú lateral para ver detalles.")

st.write("") # Espacio

# --- Tarjetas "Próximamente" (Novedad: Estilo mejorado) ---
st.header("Próximamente")
col1, col2 = st.columns(2)

with col1:
    with st.container(border=True, height=180): # height opcional para alinear
        st.subheader("📊 KPIs compradores")
        st.markdown("Visualización de tendencias históricas de consumo.")
        st.button("Ver Dashboard", disabled=True, width='stretch')

with col2:
    with st.container(border=True, height=180):
        st.subheader("⚙️ Configuración")
        st.markdown("Ajuste de parámetros globales y mapeo de SKUs.")
        st.button("Ir a Configuración", disabled=True, width='stretch')


# --- Configuración de la Barra Lateral (Sidebar) ---
st.sidebar.markdown("---")
st.sidebar.image("assets/COPEC-FLUX.svg", width='stretch') # <-- Novedad: Branding
st.sidebar.info("Seleccione una página arriba para comenzar.")
st.sidebar.markdown("---")


# --- Pie de Página (Footer) --- (Novedad)
st.markdown("---")
st.caption("© 2025 Copec Flux S.A. | Todos los derechos reservados.")
st.caption("Desarrollado por el equipo de Abastecimiento Copec Flux.")