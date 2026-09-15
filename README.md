# Maquetador de Cartas 3.3

Aplicación Streamlit para preparar imágenes de cartas a un tamaño físico y resolución de salida concretos, ajustar el recorte y procesarlas por tandas.

## 3.3

- Conserva el perfil ICC incrustado en cada imagen de entrada al generar la salida.
- No convierte el espacio de color: una imagen sRGB permanece sRGB y una Adobe RGB permanece Adobe RGB, siempre que el archivo de entrada lleve ese perfil incrustado.
- El informe `INFORME.txt` indica el perfil ICC detectado en cada imagen.
- El informe avisa de que algunas imprentas o programas prefieren Adobe RGB o un perfil ICC específico.
- Mantiene exactamente el nombre original de cada archivo dentro del ZIP.
- El tamaño en píxeles de salida y los PPP se siguen escribiendo en los metadatos de salida.

## Despliegue en Streamlit Community Cloud

Archivo principal: `streamlit_app.py`

Archivos necesarios:

```text
streamlit_app.py
requirements.txt
.streamlit/config.toml
uploader_component/__init__.py
uploader_component/index.html
```
