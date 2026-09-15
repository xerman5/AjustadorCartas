import base64
import io
import json
import re
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import streamlit as st
from PIL import Image, ImageCms, ImageDraw, ImageFilter, ImageOps, UnidentifiedImageError

from uploader_component import batch_uploader


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
MAX_MB_POR_FOTO = 12


# ============================================================
# ESTADO
# ============================================================
def init_state():
    defaults = {
        "nombre_proyecto": "Nuevo Proyecto",
        "tipo_carta": list(MEDIDAS_CARTAS.keys())[0],
        "ppp": 300,
        "nombre_input": "Nuevo Proyecto",
        "offset_porcentaje": 0.0,
        "fecha_creacion": datetime.now().strftime("%Y-%m-%d_%H-%M"),
        "json_importado": "",
        "gestion_panel": None,
        "confirmar_nuevo": False,
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


# ============================================================
# UTILIDADES
# ============================================================
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
    st.session_state.offset_porcentaje = 0.0
    st.session_state.fecha_creacion = datetime.now().strftime("%Y-%m-%d_%H-%M")
    st.session_state.json_importado = ""
    st.session_state.gestion_panel = None
    st.session_state.confirmar_nuevo = False

    st.session_state.ref_path = None
    st.session_state.ref_name = ""
    st.session_state.ref_uploader_version += 1

    st.session_state.lote = []
    st.session_state.lote_version += 1
    st.session_state.lote_ack_id = ""
    st.session_state.lote_reset_token += 1
    st.session_state.lote_advance_token += 1
    st.session_state.lote_numero = 1
    st.session_state.lote_total_tandas = 0
    st.session_state.lote_lista = False
    st.session_state.last_upload_id = ""
    st.session_state.zip_result = None


def limpiar_tanda_actual(avanzar=False):
    for item in st.session_state.lote:
        Path(item["path"]).unlink(missing_ok=True)

    st.session_state.lote = []
    st.session_state.lote_version += 1
    st.session_state.lote_ack_id = ""
    st.session_state.last_upload_id = ""
    st.session_state.lote_lista = False
    st.session_state.zip_result = None

    if avanzar:
        st.session_state.lote_numero += 1
        st.session_state.lote_advance_token += 1
    else:
        st.session_state.lote_numero = 1
        st.session_state.lote_total_tandas = 0
        st.session_state.lote_reset_token += 1


def nombre_seguro(nombre: str) -> str:
    stem = Path(nombre).stem.strip()
    stem = re.sub(r"[^\w\-.]+", "_", stem, flags=re.UNICODE)
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
    """
    Recorta primero al canvas definitivo y decide después cómo redimensionar.

    - Si el canvas recortado es igual o mayor al destino: reducción con LANCZOS.
    - Si el canvas recortado es menor: ampliación con LANCZOS + enfoque muy suave.

    La decisión de ampliar se toma sobre el área que queda después del recorte,
    no sobre las dimensiones originales de la fotografía.
    """
    box, eje = calcular_box_recorte(
        img.width, img.height, target_w, target_h, offset_p
    )
    recortada = img.crop(box)

    crop_w, crop_h = recortada.size

    # Si el canvas recortado ya coincide exactamente con la salida,
    # no hacemos absolutamente ningún procesado de redimensionado/enfoque.
    if crop_w == target_w and crop_h == target_h:
        final = recortada
        escala = 1.0
        operacion = "sin_redimensionado"

    else:
        escala = min(crop_w / target_w, crop_h / target_h)

        if escala > 1.0:
            # Hay más resolución de la necesaria: reducir con LANCZOS.
            final = recortada.resize(
                (target_w, target_h),
                Image.Resampling.LANCZOS,
            )
            operacion = "reduccion_lanczos"

        else:
            # Ampliación. Primero LANCZOS y después un enfoque
            # deliberadamente conservador para evitar halos en texto y bordes.
            ampliada = recortada.resize(
                (target_w, target_h),
                Image.Resampling.LANCZOS,
            )
            final = ampliada.filter(
                ImageFilter.UnsharpMask(
                    radius=0.6,
                    percent=35,
                    threshold=4,
                )
            )
            operacion = "ampliacion_lanczos_unsharp_suave"

    return final, box, eje, operacion, escala


def preview_con_box(img, box):
    vista = ImageOps.exif_transpose(img).convert("RGB")
    max_w = 1000
    if vista.width > max_w:
        ratio = max_w / vista.width
        vista = vista.resize(
            (max_w, max(1, int(vista.height * ratio))),
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
    draw.rectangle(
        rect,
        outline=(255, 70, 70),
        width=max(2, int(round(vista.width / 500))),
    )
    return vista


def cargar_imagen(path):
    with Image.open(path) as img:
        # Guardamos explícitamente el perfil ICC porque algunas operaciones de
        # Pillow pueden no conservarlo en el objeto resultante. No convertimos
        # los colores: simplemente transportamos el mismo perfil hasta la salida.
        icc_profile = img.info.get("icc_profile")
        corregida = ImageOps.exif_transpose(img).copy()
        if icc_profile:
            corregida.info["icc_profile"] = icc_profile
        return corregida


def nombre_perfil_icc(icc_profile):
    if not icc_profile:
        return "Sin perfil ICC incrustado"
    try:
        with ImageCms.ImageCmsProfile(io.BytesIO(icc_profile)) as profile:
            nombre = ImageCms.getProfileName(profile).strip()
            if nombre:
                return nombre
    except Exception:
        pass
    return "Perfil ICC incrustado (no identificado)"


def preparar_rgb(img):
    if img.mode == "RGB":
        return img
    icc_profile = img.info.get("icc_profile")
    if "A" in img.getbands():
        fondo = Image.new("RGB", img.size, "white")
        rgba = img.convert("RGBA")
        fondo.paste(rgba, mask=img.getchannel("A"))
    else:
        fondo = img.convert("RGB")
    if icc_profile:
        fondo.info["icc_profile"] = icc_profile
    return fondo


def guardar_upload(uploaded_file, destino: Path):
    with destino.open("wb") as f:
        f.write(uploaded_file.getbuffer())


def proyecto_json():
    return {
        "version": 3.3,
        "nombre_proyecto": st.session_state.nombre_proyecto,
        "fecha_creacion": st.session_state.fecha_creacion,
        "tipo_carta": st.session_state.tipo_carta,
        "ppp": st.session_state.ppp,
        "offset_porcentaje": st.session_state.offset_porcentaje,
    }


# ============================================================
# CABECERA + AJUSTES SIEMPRE VISIBLES
# ============================================================
st.title("🃏 Maquetador de Cartas")
st.caption("Prepara tus cartas, ajusta el recorte y descárgalas por tandas.")

col1, col2 = st.columns(2)
with col1:
    opciones_tipo = list(MEDIDAS_CARTAS.keys())
    indice_tipo = opciones_tipo.index(st.session_state.tipo_carta)
    st.session_state.tipo_carta = st.selectbox(
        "Tamaño de carta",
        opciones_tipo,
        index=indice_tipo,
    )

with col2:
    opciones_ppp = list(PPP_OPCIONES.keys())
    etiqueta_ppp = next(
        etiqueta for etiqueta, valor in PPP_OPCIONES.items()
        if valor == st.session_state.ppp
    )
    etiqueta_ppp = st.selectbox(
        "Resolución",
        opciones_ppp,
        index=opciones_ppp.index(etiqueta_ppp),
    )
    st.session_state.ppp = PPP_OPCIONES[etiqueta_ppp]

px_ancho, px_alto = dimensiones_px(
    st.session_state.tipo_carta,
    st.session_state.ppp,
)

cm_ancho, cm_alto = MEDIDAS_CARTAS[st.session_state.tipo_carta]
st.caption(
    f"Salida: {cm_ancho:.2f} × {cm_alto:.2f} cm · {px_ancho} × {px_alto} px"
)


# ============================================================
# 1 · GESTIÓN DEL PROYECTO
# ============================================================
with st.expander("1 · Proyecto", expanded=False):
    b1, b2, b3 = st.columns(3)

    with b1:
        if st.button("Nuevo", use_container_width=True):
            st.session_state.gestion_panel = "nuevo"
            st.session_state.confirmar_nuevo = True

    with b2:
        if st.button("Cargar", use_container_width=True):
            st.session_state.gestion_panel = "cargar"
            st.session_state.json_importado = ""

    with b3:
        if st.button("Grabar", use_container_width=True):
            st.session_state.gestion_panel = "grabar"

    if st.session_state.gestion_panel == "nuevo":
        st.warning("Se borrará el proyecto actual, incluidas las fotos cargadas.")
        n1, n2 = st.columns(2)
        with n1:
            if st.button("Sí, borrar todo", type="primary", use_container_width=True):
                reset_project()
                st.rerun()
        with n2:
            if st.button("Cancelar", use_container_width=True):
                st.session_state.gestion_panel = None
                st.session_state.confirmar_nuevo = False
                st.rerun()

    elif st.session_state.gestion_panel == "cargar":
        archivo_json = st.file_uploader(
            "Selecciona un proyecto (.json)",
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

                offset = max(
                    -50.0,
                    min(50.0, float(datos.get("offset_porcentaje", 0.0))),
                )

                st.session_state.nombre_proyecto = str(
                    datos.get("nombre_proyecto", "Proyecto Importado")
                )
                st.session_state.tipo_carta = tipo
                st.session_state.ppp = ppp
                st.session_state.offset_porcentaje = offset
                st.session_state.fecha_creacion = datos.get(
                    "fecha_creacion",
                    st.session_state.fecha_creacion,
                )
                st.session_state.json_importado = archivo_json.name
                st.session_state.gestion_panel = None

                st.success(
                    f"Proyecto cargado: {st.session_state.nombre_proyecto}"
                )
                st.rerun()

            except (
                json.JSONDecodeError,
                UnicodeDecodeError,
                TypeError,
                ValueError,
            ) as exc:
                st.error(f"No se pudo cargar el proyecto: {exc}")

    elif st.session_state.gestion_panel == "grabar":
        st.session_state.nombre_proyecto = st.text_input(
            "Nombre del proyecto",
            value=st.session_state.nombre_proyecto,
            key="nombre_input",
        )

        st.download_button(
            "Guardar proyecto (.json)",
            data=json.dumps(
                proyecto_json(),
                ensure_ascii=False,
                indent=2,
            ),
            file_name=(
                f"{nombre_seguro(st.session_state.nombre_proyecto)}_"
                f"{datetime.now().strftime('%Y%m%d')}.json"
            ),
            mime="application/json",
            use_container_width=True,
        )


# ============================================================
# 2 · SUBIR FOTOS EN TANDAS
# ============================================================
with st.expander("2 · Subir fotos en tandas", expanded=True):
    st.write(
        f"Selecciona todas las cartas que quieras. Se organizarán automáticamente "
        f"en tandas de {MAX_FOTOS}. Solo se envía al servidor la tanda que estés trabajando."
    )
    st.caption(f"JPG o PNG · máximo {MAX_MB_POR_FOTO} MB por foto")

    total_tandas = st.session_state.lote_total_tandas
    numero_tanda = st.session_state.lote_numero

    if total_tandas:
        st.markdown(f"**Tanda {numero_tanda} de {total_tandas}**")

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
                    raise ValueError(f"La imagen supera {MAX_MB_POR_FOTO} MB")

                numero = len(st.session_state.lote) + 1
                destino = (
                    Path(st.session_state.tmp_dir)
                    / (
                        f"t{int(upload.get('batch_number', numero_tanda)):02d}_"
                        f"{numero:02d}_"
                        f"{nombre_seguro(Path(name_original).stem)}{ext}"
                    )
                )

                destino.write_bytes(raw)

                st.session_state.lote.append({
                    "name": name_original,
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

            except (
                ValueError,
                OSError,
                base64.binascii.Error,
            ) as exc:
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

    # Estado actual
    if st.session_state.lote:
        total_actual = len(st.session_state.lote)
        numero_tanda = st.session_state.lote_numero
        total_tandas = st.session_state.lote_total_tandas

        if st.session_state.lote_lista:
            st.success(
                f"Tanda {numero_tanda} lista · {total_actual} fotos"
            )
        else:
            st.info(
                f"Cargando tanda {numero_tanda}: "
                f"{total_actual} de {MAX_FOTOS} fotos"
            )

        # Los controles del servidor no repiten la lista del componente.
        c1, c2 = st.columns(2)

        with c1:
            if st.button(
                "Vaciar tanda",
                use_container_width=True,
            ):
                limpiar_tanda_actual(avanzar=False)
                st.rerun()

        with c2:
            if st.session_state.lote_lista and st.session_state.zip_result is None:
                accion = "Ajustar y descargar fotos"
            else:
                accion = "Esperando fotos…"

            procesar = st.button(
                accion,
                type="primary",
                use_container_width=True,
                disabled=not st.session_state.lote_lista,
            )

            if procesar:
                with st.spinner("Ajustando fotos…"):
                    zip_buffer = io.BytesIO()
                    informe = [
                        "INFORME DE MAQUETACIÓN",
                        f"Proyecto: {st.session_state.nombre_proyecto}",
                        f"Tanda: {numero_tanda} / {total_tandas}",
                        f"Tamaño: {st.session_state.tipo_carta}",
                        f"Resolución: {st.session_state.ppp} PPP",
                        f"Salida: {px_ancho} × {px_alto} px",
                        f"Desplazamiento: {st.session_state.offset_porcentaje:+.1f}%",
                        "Ampliación: Lanczos + enfoque suave solo cuando el canvas recortado queda por debajo de la salida.",
                        "Color: se conserva el mismo perfil ICC incrustado en la imagen de entrada, si existe. No se realiza conversión de color.",
                        "Nota de impresión: algunas imprentas o programas prefieren Adobe RGB o un perfil ICC propio. Comprueba sus requisitos antes de imprimir.",
                        "",
                    ]

                    try:
                        with zipfile.ZipFile(
                            zip_buffer,
                            "w",
                            compression=zipfile.ZIP_DEFLATED,
                        ) as zf:
                            nombres_usados = set()

                            for item in st.session_state.lote:
                                nombre_original = item["name"]
                                ext = Path(nombre_original).suffix.lower()

                                if ext not in {".jpg", ".jpeg", ".png"}:
                                    raise ValueError(
                                        f"Formato no permitido para {nombre_original}"
                                    )

                                if nombre_original.lower() in nombres_usados:
                                    raise ValueError(
                                        f"Hay dos archivos con el mismo nombre: {nombre_original}"
                                    )

                                nombres_usados.add(nombre_original.lower())

                                img = cargar_imagen(item["path"])
                                icc_profile = img.info.get("icc_profile")
                                perfil_icc = nombre_perfil_icc(icc_profile)

                                final, box, _, operacion, escala = recortar_y_redimensionar(
                                    img,
                                    px_ancho,
                                    px_alto,
                                    st.session_state.offset_porcentaje,
                                )

                                out = io.BytesIO()

                                if ext in {".jpg", ".jpeg"}:
                                    final = preparar_rgb(final)
                                    final.save(
                                        out,
                                        format="JPEG",
                                        quality=95,
                                        optimize=True,
                                        dpi=(st.session_state.ppp, st.session_state.ppp),
                                        icc_profile=icc_profile,
                                    )
                                else:
                                    # Mantener PNG como PNG y conservar exactamente
                                    # el nombre original dentro del ZIP.
                                    final.save(
                                        out,
                                        format="PNG",
                                        optimize=True,
                                        dpi=(st.session_state.ppp, st.session_state.ppp),
                                        icc_profile=icc_profile,
                                    )

                                informe.append(
                                    f"{nombre_original} · canvas {int(round(box[2]-box[0]))}×{int(round(box[3]-box[1]))} px · {operacion} · perfil: {perfil_icc}"
                                )

                                # El nombre dentro del ZIP es EXACTAMENTE el original.
                                zf.writestr(nombre_original, out.getvalue())

                            zf.writestr(
                                "INFORME.txt",
                                "\n".join(informe),
                            )

                        st.session_state.zip_result = zip_buffer.getvalue()
                        st.success("Fotos ajustadas.")
                        st.rerun()

                    except (
                        OSError,
                        ValueError,
                        UnidentifiedImageError,
                    ) as exc:
                        st.error(f"No se pudo procesar la tanda: {exc}")

        # Descarga siempre debajo del botón de ajuste, cuando esté lista.
        if st.session_state.zip_result:
            st.download_button(
                "Descargar ZIP con fotos ajustadas",
                data=st.session_state.zip_result,
                file_name=(
                    f"{nombre_seguro(st.session_state.nombre_proyecto)}"
                    f"_tanda_{numero_tanda:02d}.zip"
                ),
                mime="application/zip",
                use_container_width=True,
                type="primary",
            )

            if numero_tanda < total_tandas:
                st.caption(
                    f"Quedan {total_tandas - numero_tanda} tandas. "
                    "Puedes continuar con la siguiente cuando hayas descargado este ZIP."
                )
                if st.button(
                    "Siguiente tanda →",
                    use_container_width=True,
                ):
                    limpiar_tanda_actual(avanzar=True)
                    st.rerun()
            else:
                st.success("Has terminado todas las tandas seleccionadas.")


# ============================================================
# 3 · AJUSTAR RECORTE
# ============================================================
with st.expander("3 · Ajustar recorte", expanded=False):
    st.write(
        "Si la carta que subes no tiene el tamaño o proporción exacta lo ajustamos, "
        "pero si quieres puedes definir un recorte preciso que se aplicará a todas las cartas."
    )
    st.caption(
        "Las ampliaciones son automáticas y conservadoras: Lanczos + enfoque suave, solo cuando el canvas recortado no alcanza la salida."
    )

    ref_file = st.file_uploader(
        f"Subir una foto de referencia · máximo {MAX_MB_POR_FOTO} MB",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=False,
        key=f"ref_uploader_{st.session_state.ref_uploader_version}",
        max_upload_size=MAX_MB_POR_FOTO,
    )

    if ref_file is not None and ref_file.name != st.session_state.ref_name:
        ref_path = (
            Path(st.session_state.tmp_dir)
            / f"referencia{Path(ref_file.name).suffix.lower()}"
        )
        guardar_upload(ref_file, ref_path)
        st.session_state.ref_path = str(ref_path)
        st.session_state.ref_name = ref_file.name

    if st.session_state.ref_path:
        try:
            img_ref = cargar_imagen(st.session_state.ref_path)
            _, _, eje, _, _ = recortar_y_redimensionar(
                img_ref,
                px_ancho,
                px_alto,
                0.0,
            )

            if eje == "X":
                st.caption(
                    "Recorte horizontal · negativo = izquierda · positivo = derecha"
                )
            elif eje == "Y":
                st.caption(
                    "Recorte vertical · negativo = abajo · positivo = arriba"
                )
            else:
                st.caption("La proporción coincide: no hace falta recortar.")

            st.session_state.offset_porcentaje = st.slider(
                "Desplazamiento del encuadre",
                -50.0,
                50.0,
                float(st.session_state.offset_porcentaje),
                0.5,
                disabled=eje is None,
                key="offset_slider",
            )

            previa, box, _, _, _ = recortar_y_redimensionar(
                img_ref,
                px_ancho,
                px_alto,
                st.session_state.offset_porcentaje,
            )
            original_marcada = preview_con_box(img_ref, box)

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

            if st.button("Quitar referencia", use_container_width=True):
                Path(st.session_state.ref_path).unlink(missing_ok=True)
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
            st.error(f"No se pudo abrir la referencia: {exc}")
    else:
        st.info("Puedes subir una foto para definir un recorte concreto.")


st.caption(
    f"{st.session_state.tipo_carta} · {st.session_state.ppp} PPP · "
    f"recorte {st.session_state.offset_porcentaje:+.1f}%"
)
