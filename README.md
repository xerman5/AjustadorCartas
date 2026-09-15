# Maquetador de Cartas · Streamlit

App de Streamlit para configurar un proyecto, ajustar el encuadre y procesar cartas por tandas.

## Estructura

```text
.
├── app.py
├── requirements.txt
├── .streamlit/
│   └── config.toml
└── uploader_component/
    ├── __init__.py
    └── index.html
```

## Streamlit Community Cloud

1. Sube todos estos archivos al repositorio de GitHub.
2. En Streamlit Community Cloud crea la app apuntando a `app.py`.
3. No necesitas instalar Node ni hacer un build del componente: el frontend es un componente V1 estático servido directamente por Streamlit.

## Uploader por lotes

El usuario puede seleccionar o arrastrar hasta 18 imágenes de una vez. El navegador comprueba el número de archivos y el tamaño individual antes de enviarlos.

Una vez pulsado «Añadir a la tanda», el componente envía las imágenes **una por una**, esperando la confirmación de Streamlit antes de continuar. De esta forma no se transmite una tanda completa de decenas o cientos de megabytes como un único mensaje.

Límites actuales:

- 18 imágenes por tanda.
- 12 MB por imagen.
- JPG/JPEG/PNG.
- 30 MB de `server.maxMessageSize`, suficiente para el mensaje de una imagen de 12 MB codificada.

## Importante

El límite de 18 se aplica en el navegador, por lo que no se utiliza `st.file_uploader(accept_multiple_files=True)` para las cartas. Esto evita que una selección masiva pase primero al uploader nativo de Streamlit.
