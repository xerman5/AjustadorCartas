import io
import json
import re
import shutil
import tempfile
import base64
import zipfile
from datetime import datetime
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

from uploader_component import batch_uploader


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
MAX_MB_POR_FOTO = 12



def init_state():
    defaults = {
        "nombre_proyecto": "Nuevo Proyecto",
        "tipo_carta": list(MEDIDAS_CARTAS.keys())[0],
        "ppp": 300,
        "nombre_input": "Nuevo Proyecto",
        "tipo_input": list(MEDIDAS_CARTAS.keys())[0],
        "ppp_input": list(PPP_OPCIONES.keys())[0],
        "offset_porcentaje": 0.0,
        "fecha_creacion": datetime.now().strftime("%Y-%m-%d_%H-%M"),
        "json_importado": "",
        "ref_path": None,
        "ref_name": "",
        "ref_uploader_version": 0,
        "lote": [],
        "lote_version": 0,
        "lote_ack_id": "",
        "lote_reset_token": 0,
        "lote_advance_token": 0,
        "lote_numero": 1,
        "lote_total_tandas": 0,
        "lote_lista": False,
        "last_upload_id": "",
        "tmp_dir": tempfile.mkdtemp(prefix="maquetador_cartas_"),
        "zip_result": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


def nueva_temporal_dir():
    old_dir = Path(st.session_state.tmp_dir)
    if old_dir.exists():
        shutil.rmtree(old_dir, ignore_errors=True)
    st.session_state.tmp_dir = tempfile.mkdtemp(prefix="maquetador_cartas_")


def reset_project():
    nueva_temporal_dir()
    st.session_state.nombre_proyecto = "Nuevo Proyecto"
    st.session_state.tipo_carta = list(MEDIDAS_CARTAS.keys())[0]
    st.session_state.ppp = 300
    st.session_state.nombre_input = "Nuevo Proyecto"
    st.session_state.tipo_input = list(MEDIDAS_CARTAS.keys())[0]
    st.session_state.ppp_input = list(PPP_OPCIONES.keys())[0]
    st.session_state.offset_porcentaje = 0.0
    st.session_state.fecha_creacion = datetime.now().strftime("%Y-%m-%d_%H-%M")
    st.session_state.json_importado = ""
    st.session_state.ref_path = None
    st.session_state.ref_name = ""
    st.session_state.ref_uploader_version += 1
    st.session_state.lote = []
    st.session_state.lote_version += 1
    st.session_state.lote_ack_id = ""
    st.session_state.lote_reset_token += 1
    st.session_state.lote_advance_token = 0
    st.session_state.lote_numero = 1
    st.session_state.lote_total_tandas = 0
    st.session_state.lote_lista = False
    st.session_state.last_upload_id = ""
    st.session_state.zip_result = None


def nombre_seguro(nombre: str) -> str:
    stem = Path(nombre).stem.strip()
    stem = re.sub(r"[^\w\-\.]+", "_", stem, flags=re.UNICODE)
    stem = re.sub(r"_+", "_", stem).strip("._")
    return stem or "carta"


def dimensiones_px(tipo_carta: str, ppp: int):
    cm_ancho, cm_alto = MEDIDAS_CARTAS[tipo_carta]
    return (
        int(round(cm_ancho / 2.54 * ppp)),
        int(round(cm_alto / 2.54 * ppp)),
    )


def calcular_box_recorte(img_w, img_h, target_w, target_h, offset_p):
    ratio_destino = target_w / target_h
    ratio_original = img_w / img_h

    if abs(ratio_original - ratio_destino) < 1e-9:
        return (0, 0, img_w, img_h), None

    if ratio_original > ratio_destino:
        ancho_requerido = img_h * ratio_destino
        exceso_x = img_w - ancho_requerido
        centro_x = max(0.0, min(1.0, 0.5 + offset_p / 100.0))
        izquierda = exceso_x * centro_x
        return (izquierda, 0, izquierda + ancho_requerido, img_h), "X"

    alto_requerido = img_w / ratio_destino
    exceso_y = img_h - alto_requerido
    centro_y = max(0.0, min(1.0, 0.5 - offset_p / 100.0))
    superior = exceso_y * centro_y
    return (0, superior, img_w, superior + alto_requerido), "Y"


def recortar_y_redimensionar(img, target_w, target_h, offset_p):
    box, eje = calcular_box_recorte(img.width, img.height, target_w, target_h, offset_p)
    recortada = img.crop(box)
    final = recortada.resize((target_w, target_h), Image.Resampling.LANCZOS)
    return final, box, eje


def preview_con_box(img, box):
    vista = ImageOps.exif_transpose(img).convert("RGB")
    max_w = 1000
    if vista.width > max_w:
        ratio = max_w / vista.width
        vista = vista.resize((max_w, max(1, int(vista.height * ratio))), Image.Resampling.LANCZOS)

    escala_x = vista.width / img.width
    escala_y = vista.height / img.height
    rect = (
        int(round(box[0] * escala_x)),
        int(round(box[1] * escala_y)),
        int(round(box[2] * escala_x)),
        int(round(box[3] * escala_y)),
    )

    draw = ImageDraw.Draw(vista)
    draw.rectangle(rect, outline=(255, 70, 70), width=max(2, int(round(vista.width / 500))))
    return vista


def cargar_imagen(path):
    with Image.open(path) as img:
        return ImageOps.exif_transpose(img).copy()


def preparar_rgb(img):
    if img.mode == "RGB":
        return img
    if "A" in img.getbands():
        fondo = Image.new("RGB", img.size, "white")
        rgba = img.convert("RGBA")
        fondo.paste(rgba, mask=img.getchannel("A"))
        return fondo
    return img.convert("RGB")


def guardar_upload(uploaded_file, destino: Path):
    with destino.open("wb") as f:
        f.write(uploaded_file.getbuffer())


st.title("🃏 Maquetador de Cartas")
st.caption("Configura el proyecto, ajusta el encuadre y procesa tus cartas por tandas.")


with st.expander("1 · Proyecto", expanded=False):
    archivo_json = st.file_uploader(
        "Cargar configuración (.json)",
        type=["json"],
        key="json_uploader",
        max_upload_size=2,
    )

    if archivo_json is not None and archivo_json.name != st.session_state.json_importado:
        try:
            datos = json.loads(archivo_json.getvalue().decode("utf-8"))
            tipo = datos.get("tipo_carta", list(MEDIDAS_CARTAS.keys())[0])
            if tipo not in MEDIDAS_CARTAS:
                tipo = list(MEDIDAS_CARTAS.keys())[0]
            ppp = int(datos.get("ppp", 300))
            if ppp not in PPP_OPCIONES.values():
                ppp = 300
            offset = max(-50.0, min(50.0, float(datos.get("offset_porcentaje", 0.0))))
            nombre = str(datos.get("nombre_proyecto", "Proyecto Importado"))

            st.session_state.nombre_proyecto = nombre
            st.session_state.tipo_carta = tipo
            st.session_state.ppp = ppp
            st.session_state.offset_porcentaje = offset
            st.session_state.nombre_input = nombre
            st.session_state.tipo_input = tipo
            st.session_state.ppp_input = next(k for k, v in PPP_OPCIONES.items() if v == ppp)
            st.session_state.fecha_creacion = datos.get("fecha_creacion", st.session_state.fecha_creacion)
            st.session_state.json_importado = archivo_json.name
            st.rerun()
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError) as exc:
            st.error(f"No se pudo cargar el JSON: {exc}")

    st.session_state.nombre_proyecto = st.text_input("Nombre", key="nombre_input")

    col1, col2 = st.columns(2)
    with col1:
        tipo = st.selectbox("Tamaño", list(MEDIDAS_CARTAS.keys()), key="tipo_input")
    with col2:
        ppp_label = st.selectbox("Resolución", list(PPP_OPCIONES.keys()), key="ppp_input")

    st.session_state.tipo_carta = tipo
    st.session_state.ppp = PPP_OPCIONES[ppp_label]

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Nuevo proyecto", use_container_width=True):
            reset_project()
            st.rerun()
    with c2:
        proyecto_json = {
            "version": 2,
            "nombre_proyecto": st.session_state.nombre_proyecto,
            "fecha_creacion": st.session_state.fecha_creacion,
            "tipo_carta": st.session_state.tipo_carta,
            "ppp": st.session_state.ppp,
            "offset_porcentaje": st.session_state.offset_porcentaje,
        }
        st.download_button(
            "Guardar JSON",
            data=json.dumps(proyecto_json, ensure_ascii=False, indent=2),
            file_name=f"{nombre_seguro(st.session_state.nombre_proyecto)}_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True,
        )


px_ancho, px_alto = dimensiones_px(st.session_state.tipo_carta, st.session_state.ppp)


with st.expander("2 · Encuadre de referencia", expanded=False):
    cm_ancho, cm_alto = MEDIDAS_CARTAS[st.session_state.tipo_carta]
    st.caption(f"Salida: {px_ancho} × {px_alto} px · {cm_ancho:.2f} × {cm_alto:.2f} cm")

    ref_file = st.file_uploader(
        f"Subir foto de referencia · máximo {MAX_MB_POR_FOTO} MB",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=False,
        key=f"ref_uploader_{st.session_state.ref_uploader_version}",
        max_upload_size=MAX_MB_POR_FOTO,
    )

    if ref_file is not None and ref_file.name != st.session_state.ref_name:
        ref_path = Path(st.session_state.tmp_dir) / f"referencia{Path(ref_file.name).suffix.lower()}"
        guardar_upload(ref_file, ref_path)
        st.session_state.ref_path = str(ref_path)
        st.session_state.ref_name = ref_file.name

    if st.session_state.ref_path:
        try:
            img_ref = cargar_imagen(st.session_state.ref_path)
            _, box0, eje = recortar_y_redimensionar(img_ref, px_ancho, px_alto, 0.0)

            if eje == "X":
                st.caption("Recorte horizontal · negativo = izquierda · positivo = derecha")
            elif eje == "Y":
                st.caption("Recorte vertical · negativo = abajo · positivo = arriba")
            else:
                st.caption("La proporción ya coincide: no hay recorte.")

            st.session_state.offset_porcentaje = st.slider(
                "Desplazamiento",
                -50.0,
                50.0,
                float(st.session_state.offset_porcentaje),
                0.5,
                disabled=eje is None,
                key="offset_slider",
            )

            previa, box, _ = recortar_y_redimensionar(
                img_ref, px_ancho, px_alto, st.session_state.offset_porcentaje
            )
            original_marcada = preview_con_box(img_ref, box)

            col1, col2 = st.columns(2)
            with col1:
                st.image(original_marcada, caption="Encuadre", use_container_width=True)
            with col2:
                st.image(previa, caption="Resultado", use_container_width=True)

            if st.button("Quitar referencia", use_container_width=True):
                Path(st.session_state.ref_path).unlink(missing_ok=True)
                st.session_state.ref_path = None
                st.session_state.ref_name = ""
                st.session_state.offset_porcentaje = 0.0
                st.session_state.ref_uploader_version += 1
                st.rerun()
        except (OSError, ValueError, UnidentifiedImageError) as exc:
            st.error(f"No se pudo abrir la referencia: {exc}")
    else:
        st.info("Sube una foto para ajustar el recorte.")


with st.expander("3 · Tandas de cartas", expanded=True):
    total_actual = len(st.session_state.lote)
    lote_lista = st.session_state.lote_lista
    total_tandas = st.session_state.lote_total_tandas
    numero_tanda = st.session_state.lote_numero

    if total_tandas:
        st.markdown(
            f"### Tanda {numero_tanda} de {total_tandas}"
        )
        st.progress(
            min(1.0, total_actual / MAX_FOTOS),
            text=f"{total_actual} / {MAX_FOTOS} fotos"
        )
    else:
        st.caption(
            f"Selecciona todas las cartas que quieras. "
            f"Se dividirán automáticamente en tandas de {MAX_FOTOS}. "
            f"Máximo {MAX_MB_POR_FOTO} MB por foto."
        )

    upload = batch_uploader(
        key="batch_uploader",
        batch_size=MAX_FOTOS,
        max_file_mb=MAX_MB_POR_FOTO,
        accepted_types=["jpg", "jpeg", "png"],
        ack_id=st.session_state.lote_ack_id,
        advance_token=st.session_state.lote_advance_token,
        reset_token=st.session_state.lote_reset_token,
        max_queue_files=500,
    )

    if upload and isinstance(upload, dict):
        upload_id = str(upload.get("upload_id", ""))

        if upload_id and upload_id != st.session_state.last_upload_id:
            try:
                name_original = str(upload.get("name", "carta.jpg"))
                ext = Path(name_original).suffix.lower()

                if ext not in {".jpg", ".jpeg", ".png"}:
                    raise ValueError("Formato no permitido")

                raw = base64.b64decode(
                    upload.get("base64", ""),
                    validate=True,
                )

                if len(raw) > MAX_MB_POR_FOTO * 1024 * 1024:
                    raise ValueError(
                        f"La imagen supera {MAX_MB_POR_FOTO} MB"
                    )

                ocupados = {
                    item["name"].lower()
                    for item in st.session_state.lote
                }

                name = name_original
                if name.lower() in ocupados:
                    base = Path(name).stem
                    contador = 2
                    candidato = f"{base}_{contador}{ext}"
                    while candidato.lower() in ocupados:
                        contador += 1
                        candidato = f"{base}_{contador}{ext}"
                    name = candidato

                numero = len(st.session_state.lote) + 1
                destino = (
                    Path(st.session_state.tmp_dir)
                    / (
                        f"t{int(upload.get('batch_number', numero_tanda)):02d}_"
                        f"{numero:02d}_"
                        f"{nombre_seguro(Path(name).stem)}{ext}"
                    )
                )

                destino.write_bytes(raw)

                st.session_state.lote.append({
                    "name": name,
                    "path": str(destino),
                    "size": len(raw),
                })

                st.session_state.lote_numero = int(
                    upload.get("batch_number", numero_tanda)
                )
                st.session_state.lote_total_tandas = int(
                    upload.get("total_batches", total_tandas or 1)
                )
                st.session_state.last_upload_id = upload_id
                st.session_state.lote_ack_id = upload_id
                st.session_state.lote_lista = False
                st.session_state.zip_result = None
                st.rerun()

            except (ValueError, OSError, base64.binascii.Error) as exc:
                st.session_state.last_upload_id = upload_id
                st.session_state.lote_ack_id = upload_id
                st.error(
                    f"No se pudo añadir {upload.get('name', 'la imagen')}: {exc}"
                )

        elif upload.get("batch_complete"):
            st.session_state.lote_numero = int(
                upload.get("batch_number", numero_tanda)
            )
            st.session_state.lote_total_tandas = int(
                upload.get("total_batches", total_tandas or 1)
            )
            st.session_state.lote_lista = True

    # --------------------------------------------------------
    # Estado de la tanda actual
    # --------------------------------------------------------
    if st.session_state.lote:
        total_actual = len(st.session_state.lote)
        total_tandas = st.session_state.lote_total_tandas
        numero_tanda = st.session_state.lote_numero

        if st.session_state.lote_lista:
            if numero_tanda < total_tandas:
                st.success(
                    f"Tanda {numero_tanda} lista · quedan "
                    f"{total_tandas - numero_tanda} tandas."
                )
            else:
                st.success("Última tanda lista.")
        else:
            st.caption(
                f"Recibidas {total_actual} de {MAX_FOTOS} fotos…"
            )

        st.divider()

        # Lista más cómoda: 10 fotos visibles aproximadamente y scroll para el resto.
        for i, item in enumerate(st.session_state.lote):
            col_a, col_b, col_c = st.columns([0.6, 3.8, 0.8])

            with col_a:
                st.write(f"**{i + 1:02d}**")

            with col_b:
                st.write(item["name"])
                st.caption(
                    f"{item['size'] / (1024 * 1024):.1f} MB"
                )

            with col_c:
                if st.button(
                    "×",
                    key=f"del_{numero_tanda}_{i}_{st.session_state.lote_version}",
                    help="Quitar de la tanda",
                ):
                    Path(item["path"]).unlink(missing_ok=True)
                    st.session_state.lote.pop(i)
                    st.session_state.lote_version += 1
                    st.session_state.zip_result = None
                    st.session_state.lote_lista = False
                    st.rerun()

        st.divider()

        # ----------------------------------------------------
        # Procesar / siguiente / limpiar
        # ----------------------------------------------------
        if st.session_state.lote_lista:
            if numero_tanda < total_tandas:
                c1, c2, c3 = st.columns([1, 1, 1])
            else:
                c1, c2 = st.columns(2)

            with c1:
                if st.button(
                    "Procesar tanda",
                    type="primary",
                    use_container_width=True,
                ):
                    with st.spinner("Procesando…"):
                        zip_buffer = io.BytesIO()
                        informe = [
                            "INFORME DE MAQUETACIÓN",
                            f"Proyecto: {st.session_state.nombre_proyecto}",
                            f"Tanda: {numero_tanda} / {total_tandas}",
                            f"Tamaño: {st.session_state.tipo_carta}",
                            f"Resolución: {st.session_state.ppp} PPP",
                            f"Salida: {px_ancho} × {px_alto} px",
                            f"Offset: {st.session_state.offset_porcentaje:+.1f}%",
                            f"Cartas procesadas: {len(st.session_state.lote)}",
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
                                    img = cargar_imagen(item["path"])
                                    final, _, _ = recortar_y_redimensionar(
                                        img,
                                        px_ancho,
                                        px_alto,
                                        st.session_state.offset_porcentaje,
                                    )
                                    final = preparar_rgb(final)

                                    base = nombre_seguro(item["name"])
                                    salida = f"{i:02d}_{base}.jpg"
                                    contador = 2

                                    while salida.lower() in nombres_usados:
                                        salida = (
                                            f"{i:02d}_{base}_{contador}.jpg"
                                        )
                                        contador += 1

                                    nombres_usados.add(salida.lower())

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
                            st.success("Tanda procesada.")

                        except (
                            OSError,
                            ValueError,
                            UnidentifiedImageError,
                        ) as exc:
                            st.error(
                                f"No se pudo procesar la tanda: {exc}"
                            )

            if numero_tanda < total_tandas:
                with c2:
                    if st.button(
                        "Siguiente tanda →",
                        use_container_width=True,
                        disabled=st.session_state.zip_result is None,
                    ):
                        for item in st.session_state.lote:
                            Path(item["path"]).unlink(missing_ok=True)

                        st.session_state.lote = []
                        st.session_state.lote_version += 1
                        st.session_state.lote_ack_id = ""
                        st.session_state.last_upload_id = ""
                        st.session_state.lote_lista = False
                        st.session_state.zip_result = None
                        st.session_state.lote_advance_token += 1
                        st.rerun()

                with c3:
                    if st.button(
                        "Cancelar selección",
                        use_container_width=True,
                    ):
                        for item in st.session_state.lote:
                            Path(item["path"]).unlink(missing_ok=True)

                        st.session_state.lote = []
                        st.session_state.lote_version += 1
                        st.session_state.lote_ack_id = ""
                        st.session_state.last_upload_id = ""
                        st.session_state.lote_lista = False
                        st.session_state.lote_total_tandas = 0
                        st.session_state.lote_numero = 1
                        st.session_state.zip_result = None
                        st.session_state.lote_reset_token += 1
                        st.rerun()

            else:
                with c2:
                    if st.button(
                        "Nueva selección",
                        use_container_width=True,
                    ):
                        for item in st.session_state.lote:
                            Path(item["path"]).unlink(missing_ok=True)

                        st.session_state.lote = []
                        st.session_state.lote_version += 1
                        st.session_state.lote_ack_id = ""
                        st.session_state.last_upload_id = ""
                        st.session_state.lote_lista = False
                        st.session_state.lote_total_tandas = 0
                        st.session_state.lote_numero = 1
                        st.session_state.zip_result = None
                        st.session_state.lote_reset_token += 1
                        st.rerun()

        else:
            # Antes de completar la tanda, solo permitimos cancelar.
            if st.button(
                "Cancelar selección",
                use_container_width=True,
            ):
                for item in st.session_state.lote:
                    Path(item["path"]).unlink(missing_ok=True)

                st.session_state.lote = []
                st.session_state.lote_version += 1
                st.session_state.lote_ack_id = ""
                st.session_state.last_upload_id = ""
                st.session_state.lote_lista = False
                st.session_state.lote_total_tandas = 0
                st.session_state.lote_numero = 1
                st.session_state.zip_result = None
                st.session_state.lote_reset_token += 1
                st.rerun()

    # --------------------------------------------------------
    # Descarga
    # --------------------------------------------------------
    if st.session_state.zip_result:
        st.download_button(
            f"Descargar ZIP · tanda {st.session_state.lote_numero}",
            data=st.session_state.zip_result,
            file_name=(
                f"{nombre_seguro(st.session_state.nombre_proyecto)}"
                f"_tanda_{st.session_state.lote_numero:02d}.zip"
            ),
            mime="application/zip",
            use_container_width=True,
            type="primary",
        )

st.caption(
    f"{st.session_state.tipo_carta} · {st.session_state.ppp} PPP · "
    f"offset {st.session_state.offset_porcentaje:+.1f}%"
)
