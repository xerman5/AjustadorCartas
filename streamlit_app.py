import streamlit as st
from PIL import Image, ImageOps
import io
import zipfile

# Configuración estética de la página web
st.set_page_config(page_title="Procesador Profesional de Cartas", page_icon="🃏", layout="centered")

st.title("🃏 Procesador de Cartas por Lote")
st.write("Sube todas tus imágenes de golpe. El sistema las adaptará y te devolverá un **archivo ZIP** con tus cartas listas y un **informe de procesamiento**.")

# --- DICCIONARIO DE MEDIDAS (Ancho x Alto en centímetros) ---
MEDIDAS_CARTAS = {
    "Estándar (Poker / MTG) - 6.35 x 8.89 cm": (6.35, 8.89),
    "Estándar Europea (Eurogames) - 5.90 x 9.20 cm": (5.90, 9.20),
    "Estándar Americana (Board Games) - 5.60 x 8.70 cm": (5.60, 8.70),
    "Mini Europea - 4.40 x 6.80 cm": (4.40, 6.80),
    "Mini Americana - 4.10 x 6.30 cm": (4.10, 6.30),
    "Tamaño Bridge - 5.72 x 8.89 cm": (5.72, 8.89)
}

# --- CONFIGURACIÓN DEL USUARIO ---
col1, col2 = st.columns(2)

with col1:
    carta_seleccionada = st.selectbox("1. Selecciona el tamaño de la carta:", list(MEDIDAS_CARTAS.keys()))

with col2:
    ppp_opciones = {
        "300 PPP (Calidad Óptima para Impresión)": 300,
        "144 PPP (Calidad Media / Borrador)": 144
    }
    ppp_seleccionado = st.selectbox("2. Selecciona la resolución de salida:", list(ppp_opciones.keys()))

# Obtener valores numéricos elegidos
cm_ancho, cm_alto = MEDIDAS_CARTAS[carta_seleccionada]
ppp_final = ppp_opciones[ppp_seleccionado]

# --- CÁLCULO MATEMÁTICO DE PÍXELES OBJETIVO ---
px_ancho = int(round((cm_ancho / 2.54) * ppp_final))
px_alto = int(round((cm_alto / 2.54) * ppp_final))

st.info(f"📐 El objetivo de impresión es: **{px_ancho} x {px_alto} píxeles** (Metadato inyectado: {ppp_final} DPI).")

# --- ZONA DE ARRASTRE DE ARCHIVOS ---
archivos_subidos = st.file_uploader(
    "3. Arrastra tus imágenes o selecciónalas todas juntas (JPG, JPEG, PNG)", 
    type=["jpg", "jpeg", "png"], 
    accept_multiple_files=True
)

# --- PROCESAMIENTO POR LOTE ---
if archivos_subidos:
    # NUEVA VALIDACIÓN: Limitar a un máximo de 15 imágenes
    if len(archivos_subidos) > 15:
        st.error(f"⚠️ No se permite subir más de 15 fotos de golpe (Has subido {len(archivos_subidos)}). Estamos en pruebas, por favor sube pequeños grupos.")
    else:
        # Creamos un contenedor de bytes para armar el ZIP en memoria sin guardar nada en el servidor
        zip_buffer = io.BytesIO()
        
        # Texto que acumulará los datos para el informe de texto
        lineas_informe = []
        lineas_informe.append("==================================================")
        lineas_informe.append("      INFORME DE PROCESAMIENTO DE IMÁGENES        ")
        lineas_informe.append("==================================================")
        lineas_informe.append(f"Tamaño elegido: {carta_seleccionada}")
        lineas_informe.append(f"Resolución de salida: {ppp_final} PPP")
        lineas_informe.append(f"Dimensiones objetivo en píxeles: {px_ancho} x {px_alto} px")
        lineas_informe.append(f"Total de imágenes procesadas: {len(archivos_subidos)}")
        lineas_informe.append("--------------------------------------------------\n")

        # Barra de progreso visual para el usuario
        barra_progreso = st.progress(0)
        status_text = st.empty()
        
        # Abrimos el archivo ZIP para empezar a meter las imágenes dentro
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as archivo_zip:
            
            for idx, archivo in enumerate(archivos_subidos):
                status_text.text(f"Procesando {idx + 1}/{len(archivos_subidos)}: {archivo.name}")
                
                img_original = Image.open(archivo)
                img_original = ImageOps.exif_transpose(img_original) # Corregir rotaciones de móviles
                
                orig_w, orig_h = img_original.size
                
                # Determinar si se agrandó o se achicó para el informe
                if (orig_w * orig_h) < (px_ancho * px_alto):
                    accion = "AGRANDADA (Upscale / Interpolación Lanzcos)"
                elif (orig_w * orig_h) > (px_ancho * px_alto):
                    accion = "ACHICADA (Downscale / Compresión de píxeles)"
                else:
                    accion = "MANTUVO TAMAÑO (Solo ajuste de proporciones)"
                    
                # Verificar si la proporción original difiere de la de destino (recorte)
                prop_original = orig_w / orig_h
                prop_destino = px_ancho / px_alto
                recorte = "SÍ (Bordes recortados para encajar proporción)" if abs(prop_original - prop_destino) > 0.01 else "NO (Encaje perfecto)"
                
                # Registrar datos en el informe para este archivo
                lineas_informe.append(f"Archivo: {archivo.name}")
                lineas_informe.append(f"  - Tamaño original: {orig_w} x {orig_h} px")
                lineas_informe.append(f"  - Acción tomada: {accion}")
                lineas_informe.append(f"  - Hubo recorte por proporción: {recorte}")
                lineas_informe.append(f"  - Resultado: {px_ancho} x {px_alto} px a {ppp_final} DPI\n")
                
                # REDIMENSIONADO INTELIGENTE Y CENTRADO
                img_procesada = ImageOps.fit(
                    img_original, 
                    (px_ancho, px_alto), 
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5)
                )
                
                # Guardamos la imagen procesada en un buffer de memoria temporal
                img_buffer = io.BytesIO()
                formato = img_original.format if img_original.format else "JPEG"
                img_procesada.save(img_buffer, format=formato, dpi=(ppp_final, ppp_final), quality=95)
                img_buffer.seek(0)
                
                # Añadir la imagen al ZIP
                nombre_final_imagen = f"LISTA_{archivo.name}"
                archivo_zip.writestr(nombre_final_imagen, img_buffer.read())
                
                # Actualizar barra de progreso web
                barra_progreso.progress((idx + 1) / len(archivos_subidos))
                
            # Al terminar todas las imágenes, generamos el archivo informe.txt en texto plano
            texto_informe = "\n".join(lineas_informe)
            archivo_zip.writestr("informe.txt", texto_informe)
            
        status_text.text("✨ ¡Todo procesado con éxito! El paquete ZIP está listo.")
        
        # Preparar el botón de descarga del ZIP completo
        zip_buffer.seek(0)
        st.write("---")
        st.download_button(
            label="📥 Descargar todas las cartas en un archivo ZIP",
            data=zip_buffer,
            file_name=f"cartas_listas_{ppp_final}ppp.zip",
            mime="application/zip",
            use_container_width=True
        )
