# Maquetador de Cartas · Streamlit

Aplicación Streamlit para ajustar un encuadre, guardar la configuración del proyecto y procesar cartas por tandas.

## Estructura

```text
app.py
requirements.txt
.streamlit/config.toml
uploader_component/__init__.py
uploader_component/index.html
```

## Subida por tandas

Puedes seleccionar muchas imágenes de una sola vez. El componente las conserva en el navegador y las divide automáticamente en tandas de 18.

Solo se envía al servidor una imagen cada vez y únicamente perteneciente a la tanda activa.

- 18 fotos por tanda
- 12 MB máximo por foto
- JPG / JPEG / PNG
- Hasta 500 archivos en la selección del navegador
- Lista con scroll de aproximadamente 10 fotos visibles

Ejemplo con 70 fotos:

- Tanda 1: 18 fotos
- Tanda 2: 18 fotos
- Tanda 3: 18 fotos
- Tanda 4: 16 fotos

La aplicación permite subir, procesar y descargar cada tanda antes de pasar a la siguiente.

## Streamlit Community Cloud

Sube todos estos archivos al repositorio de GitHub y configura `app.py` como archivo principal.

No requiere Node, npm ni un proceso de compilación del componente.
