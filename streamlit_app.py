import streamlit as st
from PIL import Image, ImageOps
import io
import zipfile
import json
from datetime import datetime

# Configuración de la página web
st.set_page_config(page_title="Maquetador Profesional de Cartas", page_icon="🃏", layout="centered")

# --- MEDIDAS DE CARTAS (Ancho x Alto en cm) ---
MEDIDAS_CARTAS = {
    "Estándar (Poker / MTG) - 6.35 x 8.89 cm": (6.35, 8.89),
    "Estándar Europea (Eurogames) - 5.90 x 9.20 cm": (5.90, 9.20),
    "Estándar Americana (Board Games) - 5.60 x 8.70 cm": (5.60, 8.70),
    "Mini Europea - 4.40 x 6.80 cm": (4.40, 6.80),
    "Mini Americana - 4.10 x 6.30 cm": (4.10, 6.30),
    "Tamaño Bridge - 5.72 x 8.89 cm": (5.72, 8.89)
}

# --- INICIALIZACIÓN DE LA MEMORIA DE SESIÓN (session_state) ---
if "nombre_proyecto" not in st.session_state:
    st.session_state.nombre_proyecto = "Nuevo Proyecto"
if "tipo_carta" not in st.session_state:
    st.session_state.tipo_carta = list(MEDIDAS_CARTAS.keys())[0]
if "ppp" not in st.session_state:
    st.session_state.ppp = 300
if "offset_porcentaje" not in st.session_state:
    st.session_state.offset_porcentaje = 0.0

# --- FUNCIONES DE GESTIÓN DE PROYECTO ---
def nuevo_proyecto():
    st.session_state.nombre_proyecto = "Nuevo Proyecto"
    st.session_state.tipo_carta = list(MEDIDAS_CARTAS.keys())[0]
    st.session_state.ppp = 300
    st.session_state.offset_porcentaje = 0.0

st.title("🃏 Maquetador de Cartas y Gestor de Proyectos")
st.write("Configura el encuadre con una foto de prueba, exporta tu proyecto en JSON y procesa cientos de cartas en tandas seguras.")

# ==========================================
# SECCIÓN 1: PANEL DE CONTROL DEL PROYECTO (JSON)
# ==========================================
st.header("📁 1. Gestión del Proyecto")
expander_proyecto = st.expander("Configuración y exportación de archivos JSON", expanded=True)

with expander_proyecto:
    # Cargar JSON existente
    archivo_json = st.file_uploader("Importar proyecto existente (.json)", type=["json"])
    if archivo_json is not None:
        try:
            datos_proyecto = json.load(archivo_json)
            st.session_state.nombre_proyecto = datos_proyecto.get("nombre_proyecto", "Proyecto Importado")
            st.session_state.tipo_carta = datos_proyecto.get("tipo_carta", list(MEDIDAS_CARTAS.keys())[0])
            st.session_state.ppp = datos_proyecto.get("ppp", 300)
            st.session_state.offset_porcentaje = datos_proyecto.get("offset_porcentaje", 0.0)
            st.success(f"✅ ¡Proyecto '{st.session_state.nombre_proyecto}' cargado con éxito!")
        except Exception as e:
            st.error(f"Error al leer el archivo JSON: {e}")

    # Campos del proyecto actual
    st.session_state.nombre_proyecto = st.text_input("Nombre del proyecto:", value=st.session_state.nombre_proyecto)
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.session_state.tipo_carta = st.selectbox(
            "Tamaño de carta destino:", list(MEDIDAS_CARTAS.keys()), 
            index=list(MEDIDAS_CARTAS.keys()).index(st.session_state.tipo_carta)
        )
    with col_p2:
        opciones_ppp = {"300 PPP (Óptimo)": 300, "144 PPP (Borrador)": 144}
        index_ppp = 0 if st.session_state.ppp == 300 else 1
        seleccion_ppp = st.selectbox("Resolución de salida:", list(opciones_ppp.keys()), index=index_ppp)
        st.session_state.ppp = opciones_ppp[seleccion_ppp]

    # Botones de Acción
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        st.button("✨ Iniciar Nuevo Proyecto (Borrar todo)", on_click=nuevo_proyecto, use_container_width=True)
    with col_b2:
        # Estructura del JSON para descarga
        json_exportar = {
            "nombre_proyecto": st.session_state.nombre_proyecto,
            "fecha_creacion": datetime.now().strftime("%Y-%m-%d_%H-%M"),
            "tipo_carta": st.session_state.tipo_carta,
            "ppp": st.session_state.ppp,
            "offset_porcentaje": st.session_state.offset_porcentaje
        }
        json_str = json.dumps(json_exportar, indent=2)
        fecha_str = datetime.now().strftime("%Y%m%d")
        st.download_button(
            label="💾 Exportar Configuración Proyecto (.json)",
            data=json_str,
            file_name=f"{st.session_state.nombre_proyecto.replace(' ', '_')}_{fecha_str}.json",
            mime="application/json",
            use_container_width=True
        )

# --- CÁLCULO DE DIMENSIONES ---
cm_ancho, cm_alto = MEDIDAS_CARTAS[st.session_state.tipo_carta]
px_ancho = int(round((cm_ancho / 2.54) * st.session_state.ppp))
px_alto = int(round((cm_alto / 2.54) * st.session_state.ppp))

# ==========================================
# SECCIÓN 2: FOTO DE REFERENCIA Y ENCUADRE
# ==========================================
st.header("📸 2. Configurar Encuadre de Referencia")
st.write("Sube una imagen de muestra para ajustar qué zona se recortará si la proporción no encaja perfectamente.")

# Inicializar almacenamiento de la imagen de referencia en la sesión
if "img_ref_cache" not in st.session_state:
    st.session_state.img_ref_cache = None
if "nombre_ref_cache" not in st.session_state:
    st.session_state.nombre_ref_cache = ""

foto_referencia = st.file_uploader("Subir UNA foto de prueba:", type=["jpg", "jpeg", "png"], key="ref_uploader")

# Si el usuario sube un archivo nuevo, lo guardamos en la sesión
if foto_referencia is not None and foto_referencia.name != st.session_state.nombre_ref_cache:
    img_abierta = Image.open(foto_referencia)
    st.session_state.img_ref_cache = ImageOps.exif_transpose(img_abierta)
    st.session_state.nombre_ref_cache = foto_referencia.name
# Si el usuario quita la foto, limpiamos la sesión
elif foto_referencia is None:
    st.session_state.img_ref_cache = None
    st.session_state.nombre_ref_cache = ""

# Función de recorte manual basada en el desplazamiento porcentual del usuario
def recortar_con_offset(img, target_w, target_h, offset_p):
    img_w, img_h = img.size
    ratio_destino = target_w / target_h
    ratio_original = img_w / img_h
    
    if ratio_original > ratio_destino:
        # Sobra espacio en el ancho (Eje X)
        ancho_requerido = img_h * ratio_destino
        exceso_x = img_w - ancho_requerido
        centro_x = 0.5 + (offset_p / 100.0)
        centro_x = max(0.0, min(1.0, centro_x))
        
        izq = exceso_x * centro_x - (ancho_requerido / 2)
        izq = max(0, min(img_w - ancho_requerido, izq))
        box = (izq, 0, izq + ancho_requerido, img_h)
        eje_afectado = "X"
    else:
        # Sobra espacio en el alto (Eje Y)
        alto_requerido = img_w / ratio_destino
        exceso_y = img_h - alto_requerido
        centro_y = 0.5 - (offset_p / 100.0) # Positivo = subir encuadre
        centro_y = max(0.0, min(1.0, centro_y))
        
        sup = exceso_y * centro_y - (alto_requerido / 2)
        sup = max(0, min(img_h - alto_requerido, sup))
        box = (0, sup, img_w, sup + alto_requerido)
        eje_afectado = "Y"
        
    img_recortada = img.crop(box)
    img_final = img_recortada.resize((target_w, target_h), Image.Resampling.LANCZOS)
    return img_final, eje_afectado

# Si hay una imagen en la memoria de la sesión, procesamos la vista
if st.session_state.img_ref_cache is not None:
    img_ref = st.session_state.img_ref_cache
    
    # Renderizar el recorte inicial simulado para saber qué eje se ve afectado
    _, eje = recortar_con_offset(img_ref, px_ancho, px_alto, 0.0)
    
    st.write(f"Proporción de carta detectada. El eje sobrante que sufrirá el recorte es el **Eje {eje}**.")
    
    # Controladores del slider vinculados directamente a la sesión
    if eje == "X":
        st.session_state.offset_porcentaje = st.slider(
            "Desplazamiento horizontal del encuadre (%):", 
            min_value=-50.0, max_value=50.0, value=float(st.session_state.offset_porcentaje), step=0.5,
            key="slider_eje_x"
        )
    else:
        st.session_state.offset_porcentaje = st.slider(
            "Desplazamiento vertical del encuadre (%):", 
            min_value=-50.0, max_value=50.0, value=float(st.session_state.offset_porcentaje), step=0.5,
            key="slider_eje_y"
        )
        
    # Generar previsualización con el offset activo
    img_previa, _ = recortar_con_offset(img_ref, px_ancho, px_alto, st.session_state.offset_porcentaje)
    
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.image(img_ref, caption="Imagen Original", use_container_width=True)
    with col_v2:
        st.image(img_previa, caption=f"Resultado final en carta ({px_ancho}x{px_alto} px)", use_container_width=True)


# ==========================================
# SECCIÓN 3: PROCESAMIENTO DE LOTES (TANDAS)
# ==========================================
st.header("📦 3. Carga e Impresión de Cartas por Tanda")
st.write(f"Las imágenes se recortarán siguiendo el patrón guardado (**Eje de desplazamiento: {st.session_state.offset_porcentaje}%**).")

archivos_lote = st.file_uploader(
    "Sube tus imágenes en grupos (Máximo 18 por tanda para proteger la estabilidad del servidor):", 
    type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="lote_uploader"
)

if archivos_lote:
    total_lote = len(archivos_lote)
    if total_lote > 18:
        st.error(f"⚠️ **Límite de seguridad superado:** Has subido {total_lote} imágenes. Elimina {total_lote - 18} archivos de la lista de abajo haciendo clic en su icono de papelera (X) para poder procesar.")
        st.stop()
    else:
        st.success(f"📸 **Tanda válida:** {total_lote} de 18 archivos listos. Haz clic abajo para procesar.")

    if st.button("🚀 Procesar Tanda y Generar Archivo ZIP", use_container_width=True):
        zip_buffer = io.BytesIO()
        lineas_informe = [
            "==================================================",
            "      INFORME DE MAQUETACIÓN POR LOTE             ",
            f"      PROYECTO: {st.session_state.nombre_proyecto.upper()} ",
            "==================================================",
            f"Configuración del Lienzo: {st.session_state.tipo_carta}",
            f"Resolución Inyectada: {st.session_state.ppp} PPP",
            f"Dimensiones de Impresión: {px_ancho} x {px_alto} px",
            f"Desplazamiento Porcentual Aplicado: {st.session_state.offset_porcentaje}%",
            "--------------------------------------------------\n"
        ]
        
