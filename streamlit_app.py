import io
import json
import re
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError


# ============================================================
# CONFIGURACIÓN
# ============================================================
st.set_page_config(
    page_title="Maquetador de Cartas",
    page_icon="🃏",
    layout="centered",
)

MEDIDAS_CARTAS = {
    "Estándar (Poker / MTG) · 6,35 × 8,89 cm": (6.35, 8.89),
    "Estándar Europea (Eurogames) · 5,90 × 9,20 cm": (5.90, 9.20),
    "Estándar Americana (Board Games) · 5,60 × 8,70 cm": (5.60, 8.70),
    "Mini Europea · 4,40 × 6,80 cm": (4.40, 6.80),
    "Mini Americana · 4,10 × 6,30 cm": (4.10, 6.30),
    "Tamaño Bridge · 5,72 × 8,89 cm": (5.72, 8.89),
}

PPP_OPCIONES = {
    "300 PPP · impresión": 300,
    "144 PPP · borrador": 144,
}

MAX_FOTOS = 18
MAX_MB_POR_FOTO = 20


# ============================================================
# ESTADO DE SESIÓN
# ============================================================
def init_state():
    defaults = {
        "nombre_proyecto": "Nuevo Proyecto",
        "tipo_carta": list(MEDIDAS_CARTAS.keys())[0],
        "ppp": 300,

        # Valores de los widgets
        "nombre_input": "Nuevo Proyecto",
        "tipo_input": list(MEDIDAS_CARTAS.keys())[0],
        "ppp_input": list(PPP_OPCIONES.keys())[0],

        "offset_porcentaje": 0.0,
        "fecha_creacion": datetime.now().strftime("%Y-%m-%d_%H-%M"),

        "json_importado": "",

        # Referencia
        "ref_path": None,
        "ref_name": "",
        "ref_uploader_version": 0,

        # Lote
        "lote": [],
        "lote_uploader_version": 0,

        # Temporales
        "tmp_dir": tempfile.mkdtemp(prefix="maquetador_cartas_"),

        # ZIP generado
        "zip_result": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


# ============================================================
# UTILIDADES
# ============================================================
def nueva_temporal_dir():
    old_dir = Path(st.session_state.tmp_dir)

    if old_dir.exists():
        shutil.rmtree(old_dir, ignore_errors=True)

    st.session_state.tmp_dir = tempfile.mkdtemp(
        prefix="maquetador_cartas_"
    )


def reset_project():
    nueva_temporal_dir()

    st.session_state.nombre_proyecto = "Nuevo Proyecto"
    st.session_state.tipo_carta = list(MEDIDAS_CARTAS.keys())[0]
    st.session_state.ppp = 300

    st.session_state.nombre_input = "Nuevo Proyecto"
    st.session_state.tipo_input = list(MEDIDAS_CARTAS.keys())[0]
    st.session_state.ppp_input = list(PPP_OPCIONES.keys())[0]

    st.session_state.offset_porcentaje = 0.0

    st.session_state.fecha_creacion = datetime.now().strftime(
        "%Y-%m-%d_%H-%M"
    )

    st.session_state.json_importado = ""

    # Referencia
    st.session_state.ref_path = None
    st.session_state.ref_name = ""
    st.session_state.ref_uploader_version += 1

    # Lote
    st.session_state.lote = []
    st.session_state.lote_uploader_version += 1

    st.session_state.zip_result = None


def nombre_seguro(nombre: str) -> str:
    stem = Path(nombre).stem.strip()

    stem = re.sub(
        r"[^\w\-\.]+",
        "_",
        stem,
        flags=re.UNICODE,
    )

    stem = re.sub(r"_+", "_", stem).strip("._")

    return stem or "carta"


def dimensiones_px(tipo_carta: str, ppp: int):
    cm_ancho, cm_alto = MEDIDAS_CARTAS[tipo_carta]

    return (
        int(round(cm_ancho / 2.54 * ppp)),
        int(round(cm_alto / 2.54 * ppp)),
    )


def calcular_box_recorte(
    img_w: int,
    img_h: int,
    target_w: int,
    target_h: int,
    offset_p: float,
):
    """
    Calcula el área de recorte.

    X:
        -50 = máxima izquierda
         0  = centro
        +50 = máxima derecha

    Y:
        -50 = máxima abajo
         0  = centro
        +50 = máxima arriba
    """

    ratio_destino = target_w / target_h
    ratio_original = img_w / img_h

    if abs(ratio_original - ratio_destino) < 1e-9:
        return (0, 0, img_w, img_h), None

    # --------------------------------------------------------
    # Sobra anchura
    # --------------------------------------------------------
    if ratio_original > ratio_destino:

        ancho_requerido = img_h * ratio_destino
        exceso_x = img_w - ancho_requerido

        centro_x = 0.5 + (offset_p / 100.0)
        centro_x = max(0.0, min(1.0, centro_x))

        izquierda = exceso_x * centro_x

        box = (
            izquierda,
            0,
            izquierda + ancho_requerido,
            img_h,
        )

        return box, "X"

    # --------------------------------------------------------
    # Sobra altura
    # --------------------------------------------------------
    alto_requerido = img_w / ratio_destino
    exceso_y = img_h - alto_requerido

    # Positivo = subir
    centro_y = 0.5 - (offset_p / 100.0)
    centro_y = max(0.0, min(1.0, centro_y))

    superior = exceso_y * centro_y

    box = (
        0,
        superior,
        img_w,
        superior + alto_requerido,
    )

    return box, "Y"


def recortar_y_redimensionar(
    img: Image.Image,
    target_w: int,
    target_h: int,
    offset_p: float,
):
    box, eje = calcular_box_recorte(
        img.width,
        img.height,
        target_w,
        target_h,
        offset_p,
    )

    recortada = img.crop(box)

    final = recortada.resize(
        (target_w, target_h),
        Image.Resampling.LANCZOS,
    )

    return final, box, eje


def preview_con_box(img: Image.Image, box):
    """
    Crea una copia de preview con el área de recorte marcada.
    """

    vista = ImageOps.exif_transpose(img).convert("RGB")

    max_w = 1000

    if vista.width > max_w:
        ratio = max_w / vista.width

        vista = vista.resize(
            (
                max_w,
                max(1, int(vista.height * ratio)),
            ),
            Image.Resampling.LANCZOS,
        )

    escala_x = vista.width / img.width
    escala_y = vista.height / img.height

    rect = (
        int(round(box[0] * escala_x)),
        int(round(box[1] * escala_y)),
        int(round(box[2] * escala_x)),
        int(round(box[3] * escala_y)),
    )

    draw = ImageDraw.Draw(vista)

    grosor = max(
        2,
        int(round(vista.width / 500)),
    )

    draw.rectangle(
        rect,
        outline=(255, 70, 70),
        width=grosor,
    )

    return vista


def cargar_imagen(path: str) -> Image.Image:
    with Image.open(path) as img:
        return ImageOps.exif_transpose(img).copy()


def preparar_rgb(img: Image.Image) -> Image.Image:
    if img.mode == "RGB":
        return img

    if "A" in img.getbands():
        fondo = Image.new(
            "RGB",
            img.size,
            "white",
        )

        rgba = img.convert("RGBA")

        fondo.paste(
            rgba,
            mask=img.getchannel("A"),
        )

        return fondo

    return img.convert("RGB")


def guardar_upload(uploaded_file, destino: Path):
    with destino.open("wb") as f:
        f.write(uploaded_file.getbuffer())


# ============================================================
# CABECERA
# ============================================================
st.title("🃏 Maquetador de Cartas")

st.caption(
    "Configura el proyecto, ajusta el encuadre y añade las cartas una a una."
)


# ============================================================
# 1 · PROYECTO
# ============================================================
with st.expander("1 · Proyecto", expanded=False):

    archivo_json = st.file_uploader(
        "Cargar configuración (.json)",
        type=["json"],
        key="json_uploader",
        max_upload_size=2,
    )

    # --------------------------------------------------------
    # Importar JSON
    # --------------------------------------------------------
    if (
        archivo_json is not None
        and archivo_json.name != st.session_state.json_importado
    ):
        try:
            datos = json.loads(
                archivo_json.getvalue().decode("utf-8")
            )

            tipo = datos.get(
                "tipo_carta",
                list(MEDIDAS_CARTAS.keys())[0],
            )

            if tipo not in MEDIDAS_CARTAS:
                tipo = list(MEDIDAS_CARTAS.keys())[0]

            ppp = int(
                datos.get("ppp", 300)
            )

            if ppp not in PPP_OPCIONES.values():
                ppp = 300

            offset = float(
                datos.get(
                    "offset_porcentaje",
                    0.0,
                )
            )

            offset = max(
                -50.0,
                min(50.0, offset),
            )

            nombre = str(
                datos.get(
                    "nombre_proyecto",
                    "Proyecto Importado",
                )
            )

            st.session_state.nombre_proyecto = nombre
            st.session_state.tipo_carta = tipo
            st.session_state.ppp = ppp
            st.session_state.offset_porcentaje = offset

            st.session_state.nombre_input = nombre
            st.session_state.tipo_input = tipo
            st.session_state.ppp_input = next(
                k for k, v in PPP_OPCIONES.items()
                if v == ppp
            )

            st.session_state.fecha_creacion = datos.get(
                "fecha_creacion",
                datetime.now().strftime(
                    "%Y-%m-%d_%H-%M"
                ),
            )

            st.session_state.json_importado = (
                archivo_json.name
            )

            st.success(
                f"Configuración cargada: {nombre}"
            )

            st.rerun()

        except (
            json.JSONDecodeError,
            UnicodeDecodeError,
            TypeError,
            ValueError,
        ) as exc:

            st.error(
                f"No se pudo cargar el JSON: {exc}"
            )

    # --------------------------------------------------------
    # Campos
    # --------------------------------------------------------
    st.session_state.nombre_proyecto = st.text_input(
        "Nombre",
        key="nombre_input",
    )

    col1, col2 = st.columns(2)

    with col1:
        tipo = st.selectbox(
            "Tamaño",
            list(MEDIDAS_CARTAS.keys()),
            key="tipo_input",
        )

    with col2:
        ppp_label = st.selectbox(
            "Resolución",
            list(PPP_OPCIONES.keys()),
            key="ppp_input",
        )

    st.session_state.tipo_carta = tipo
    st.session_state.ppp = PPP_OPCIONES[ppp_label]

    # --------------------------------------------------------
    # Botones
    # --------------------------------------------------------
    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "Nuevo proyecto",
            use_container_width=True,
        ):
            reset_project()
            st.rerun()

    with c2:

        proyecto_json = {
            "version": 2,
            "nombre_proyecto": (
                st.session_state.nombre_proyecto
            ),
            "fecha_creacion": (
                st.session_state.fecha_creacion
            ),
            "tipo_carta": (
                st.session_state.tipo_carta
            ),
            "ppp": (
                st.session_state.ppp
            ),
            "offset_porcentaje": (
                st.session_state.offset_porcentaje
            ),
        }

        json_data = json.dumps(
            proyecto_json,
            ensure_ascii=False,
            indent=2,
        )

        fecha = datetime.now().strftime(
            "%Y%m%d"
        )

        st.download_button(
            "Guardar JSON",
            data=json_data,
            file_name=(
                f"{nombre_seguro(st.session_state.nombre_proyecto)}"
                f"_{fecha}.json"
            ),
            mime="application/json",
            use_container_width=True,
        )


# ============================================================
# DIMENSIONES DE SALIDA
# ============================================================
px_ancho, px_alto = dimensiones_px(
    st.session_state.tipo_carta,
    st.session_state.ppp,
)


# ============================================================
# 2 · ENCUADRE
# ============================================================
with st.expander(
    "2 · Encuadre de referencia",
    expanded=False,
):

    cm_ancho, cm_alto = MEDIDAS_CARTAS[
        st.session_state.tipo_carta
    ]

    st.caption(
        f"Salida: {px_ancho} × {px_alto} px · "
        f"{cm_ancho:.2f} × {cm_alto:.2f} cm"
    )

    ref_file = st.file_uploader(
        f"Subir foto de referencia · máximo {MAX_MB_POR_FOTO} MB",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=False,
        key=(
            f"ref_uploader_"
            f"{st.session_state.ref_uploader_version}"
        ),
        max_upload_size=MAX_MB_POR_FOTO,
    )

    if (
        ref_file is not None
        and ref_file.name != st.session_state.ref_name
    ):
        ref_path = (
            Path(st.session_state.tmp_dir)
            / f"referencia{Path(ref_file.name).suffix.lower()}"
        )

        guardar_upload(
            ref_file,
            ref_path,
        )

        st.session_state.ref_path = str(
            ref_path
        )

        st.session_state.ref_name = (
            ref_file.name
        )

    if st.session_state.ref_path:

        try:
            img_ref = cargar_imagen(
                st.session_state.ref_path
            )

            _, box0, eje = recortar_y_redimensionar(
                img_ref,
                px_ancho,
                px_alto,
                0.0,
            )

            if eje == "X":
                texto_eje = "Horizontal"
                ayuda = (
                    "Negativo = izquierda · "
                    "positivo = derecha"
                )

            elif eje == "Y":
                texto_eje = "Vertical"
                ayuda = (
                    "Negativo = abajo · "
                    "positivo = arriba"
                )

            else:
                texto_eje = "Ninguno"
                ayuda = (
                    "La proporción ya coincide"
                )

            st.write(
                f"Recorte: **{texto_eje}**"
            )

            st.caption(ayuda)

            st.session_state.offset_porcentaje = st.slider(
                "Desplazamiento del encuadre",
                min_value=-50.0,
                max_value=50.0,
                step=0.5,
                disabled=eje is None,
                key="offset_slider",
            )

            previa, box, _ = (
                recortar_y_redimensionar(
                    img_ref,
                    px_ancho,
                    px_alto,
                    st.session_state.offset_porcentaje,
                )
            )

            original_marcada = preview_con_box(
                img_ref,
                box,
            )

            col1, col2 = st.columns(2)

            with col1:
                st.image(
                    original_marcada,
                    caption="Encuadre",
                    use_container_width=True,
                )

            with col2:
                st.image(
                    previa,
                    caption="Resultado",
                    use_container_width=True,
                )

            if st.button(
                "Quitar referencia",
                use_container_width=True,
            ):

                ref_path = Path(
                    st.session_state.ref_path
                )

                if ref_path.exists():
                    ref_path.unlink(
                        missing_ok=True
                    )

                st.session_state.ref_path = None
                st.session_state.ref_name = ""
                st.session_state.offset_porcentaje = 0.0
                st.session_state.ref_uploader_version += 1

                st.rerun()

        except (
            OSError,
            ValueError,
            UnidentifiedImageError,
        ) as exc:

            st.error(
                f"No se pudo abrir la referencia: {exc}"
            )

    else:
        st.info(
            "Sube una foto para ajustar el recorte."
        )


# ============================================================
# 3 · LOTE
# ============================================================
with st.expander(
    "3 · Tanda de cartas",
    expanded=True,
):

    total_actual = len(
        st.session_state.lote
    )

    st.write(
        f"Máximo **{MAX_FOTOS} cartas** por tanda."
    )

    st.progress(
        total_actual / MAX_FOTOS,
        text=(
            f"{total_actual} / {MAX_FOTOS} cartas"
        ),
    )

    # --------------------------------------------------------
    # Subir siguiente carta
    # --------------------------------------------------------
    if total_actual < MAX_FOTOS:

        lote_file = st.file_uploader(
            f"Añadir carta · máximo {MAX_MB_POR_FOTO} MB",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=False,
            key=(
                f"lote_uploader_"
                f"{st.session_state.lote_uploader_version}"
            ),
            max_upload_size=MAX_MB_POR_FOTO,
        )

        if lote_file is not None:

            st.caption(
                f"{lote_file.name} · "
                f"{lote_file.size / (1024 * 1024):.1f} MB"
            )

            if st.button(
                "Añadir a la tanda",
                type="primary",
                use_container_width=True,
            ):

                ext = Path(
                    lote_file.name
                ).suffix.lower()

                destino = (
                    Path(st.session_state.tmp_dir)
                    / (
                        f"entrada_"
                        f"{len(st.session_state.lote) + 1:02d}"
                        f"{ext}"
                    )
                )

                try:
                    guardar_upload(
                        lote_file,
                        destino,
                    )

                    st.session_state.lote.append(
                        {
                            "name": lote_file.name,
                            "path": str(destino),
                            "size": lote_file.size,
                        }
                    )

                    st.session_state.zip_result = None
                    st.session_state.lote_uploader_version += 1

                    st.rerun()

                except OSError as exc:
                    st.error(
                        f"No se pudo guardar la foto: {exc}"
                    )

    else:
        st.success(
            "Tanda completa."
        )

    # --------------------------------------------------------
    # Lista de fotos
    # --------------------------------------------------------
    if st.session_state.lote:

        for i, item in enumerate(
            st.session_state.lote
        ):

            col_a, col_b, col_c = st.columns(
                [0.7, 2.8, 0.9]
            )

            with col_a:
                st.write(
                    f"**{i + 1:02d}**"
                )

            with col_b:
                st.write(
                    item["name"]
                )

            with col_c:
                if st.button(
                    "×",
                    key=f"del_{i}",
                    help="Quitar de la tanda",
                ):

                    path = Path(
                        item["path"]
                    )

                    path.unlink(
                        missing_ok=True
                    )

                    st.session_state.lote.pop(i)
                    st.session_state.zip_result = None

                    st.rerun()

        st.divider()

        c1, c2 = st.columns(2)

        # ----------------------------------------------------
        # Limpiar
        # ----------------------------------------------------
        with c1:

            if st.button(
                "Limpiar tanda",
                use_container_width=True,
            ):

                for item in st.session_state.lote:
                    Path(
                        item["path"]
                    ).unlink(
                        missing_ok=True
                    )

                st.session_state.lote = []
                st.session_state.lote_uploader_version += 1
                st.session_state.zip_result = None

                st.rerun()

        # ----------------------------------------------------
        # Procesar
        # ----------------------------------------------------
        with c2:

            if st.button(
                "Procesar tanda",
                type="primary",
                use_container_width=True,
            ):

                with st.spinner(
                    "Procesando imágenes…"
                ):

                    zip_buffer = io.BytesIO()

                    informe = [
                        "INFORME DE MAQUETACIÓN",
                        f"Proyecto: {st.session_state.nombre_proyecto}",
                        f"Tamaño: {st.session_state.tipo_carta}",
                        f"Resolución: {st.session_state.ppp} PPP",
                        f"Salida: {px_ancho} × {px_alto} px",
                        (
                            "Offset: "
                            f"{st.session_state.offset_porcentaje:+.1f}%"
                        ),
                        (
                            "Cartas procesadas: "
                            f"{len(st.session_state.lote)}"
                        ),
                        "",
                    ]

                    try:

                        with zipfile.ZipFile(
                            zip_buffer,
                            "w",
                            compression=zipfile.ZIP_DEFLATED,
                        ) as zf:

                            nombres_usados = set()

                            for i, item in enumerate(
                                st.session_state.lote,
                                start=1,
                            ):

                                img = cargar_imagen(
                                    item["path"]
                                )

                                final, _, _ = (
                                    recortar_y_redimensionar(
                                        img,
                                        px_ancho,
                                        px_alto,
                                        st.session_state.offset_porcentaje,
                                    )
                                )

                                final = preparar_rgb(
                                    final
                                )

                                base = nombre_seguro(
                                    item["name"]
                                )

                                salida = (
                                    f"{i:02d}_{base}.jpg"
                                )

                                contador = 2

                                while (
                                    salida.lower()
                                    in nombres_usados
                                ):
                                    salida = (
                                        f"{i:02d}_"
                                        f"{base}_"
                                        f"{contador}.jpg"
                                    )

                                    contador += 1

                                nombres_usados.add(
                                    salida.lower()
                                )

                                out = io.BytesIO()

                                final.save(
                                    out,
                                    format="JPEG",
                                    quality=95,
                                    optimize=True,
                                    dpi=(
                                        st.session_state.ppp,
                                        st.session_state.ppp,
                                    ),
                                )

                                zf.writestr(
                                    salida,
                                    out.getvalue(),
                                )

                            zf.writestr(
                                "INFORME.txt",
                                "\n".join(informe),
                            )

                        st.session_state.zip_result = (
                            zip_buffer.getvalue()
                        )

                        st.success(
                            "Tanda procesada correctamente."
                        )

                    except (
                        OSError,
                        ValueError,
                        UnidentifiedImageError,
                    ) as exc:

                        st.error(
                            f"No se pudo procesar la tanda: {exc}"
                        )

    # --------------------------------------------------------
    # Descarga
    # --------------------------------------------------------
    if st.session_state.zip_result:

        st.download_button(
            "Descargar ZIP",
            data=st.session_state.zip_result,
            file_name=(
                f"{nombre_seguro(st.session_state.nombre_proyecto)}"
                "_cartas.zip"
            ),
            mime="application/zip",
            use_container_width=True,
            type="primary",
        )


# ============================================================
# PIE
# ============================================================
st.caption(
    f"{st.session_state.tipo_carta} · "
    f"{st.session_state.ppp} PPP · "
    f"offset {st.session_state.offset_porcentaje:+.1f}%"
)
