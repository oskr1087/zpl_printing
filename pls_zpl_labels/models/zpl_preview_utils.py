import base64
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont

from odoo import _
from odoo.exceptions import UserError


LABELARY_BASE_URL = "https://api.labelary.com/v1/printers/12dpmm/labels"


def render_qweb_text(records, report_xmlid):
    """Renderiza exactamente el mismo QWeb-text/ZPL utilizado para imprimir."""
    if not records:
        return ""
    zpl_bytes, _report_type = records.env["ir.actions.report"]._render_qweb_text(
        report_xmlid,
        records.ids,
    )
    return zpl_bytes.decode("utf-8") if isinstance(zpl_bytes, bytes) else zpl_bytes


def _labelary_png_bytes(zpl_code, width, height):
    url = f"{LABELARY_BASE_URL}/{width}x{height}/0/"
    try:
        response = requests.post(
            url,
            headers={"Accept": "image/png"},
            data=(zpl_code or "").encode("utf-8"),
            timeout=12,
        )
    except requests.exceptions.RequestException as exc:
        raise UserError(
            _("No se pudo generar la vista previa de la etiqueta con Labelary:\n%s")
            % str(exc)
        ) from exc

    if response.status_code != 200:
        detail = response.text[:1000] if response.text else _("Respuesta sin detalle")
        raise UserError(
            _("Labelary devolvió el error %(status)s:\n%(detail)s")
            % {"status": response.status_code, "detail": detail}
        )
    return response.content


def labelary_png(zpl_code, width, height):
    """Devuelve una vista previa PNG generada desde el ZPL real."""
    return base64.b64encode(_labelary_png_bytes(zpl_code, width, height))


def labelary_multi_png(zpl_code, width, height):
    """Genera una sola imagen vertical con todas las etiquetas del ZPL."""
    chunks = []
    for part in (zpl_code or "").split("^XZ"):
        part = part.strip()
        if not part:
            continue
        if "^XA" not in part:
            continue
        chunks.append(part + "\n^XZ")

    if not chunks:
        return labelary_png(zpl_code, width, height)

    images = []
    for chunk in chunks:
        raw = _labelary_png_bytes(chunk, width, height)
        images.append(Image.open(BytesIO(raw)).convert("RGB"))

    if len(images) == 1:
        out = BytesIO()
        images[0].save(out, format="PNG")
        return base64.b64encode(out.getvalue())

    gap = 24
    canvas_width = max(image.width for image in images)
    canvas_height = sum(image.height for image in images) + gap * (len(images) - 1)
    canvas = Image.new("RGB", (canvas_width, canvas_height), "white")
    y = 0
    for image in images:
        x = (canvas_width - image.width) // 2
        canvas.paste(image, (x, y))
        y += image.height + gap

    out = BytesIO()
    canvas.save(out, format="PNG")
    return base64.b64encode(out.getvalue())


def _font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _location_color_preview(record, zpl_code):
    """Vista previa a color de ubicación usando como base el ZPL real."""
    raw = _labelary_png_bytes(zpl_code, 4, 6)
    image = Image.open(BytesIO(raw)).convert("RGB")
    draw = ImageDraw.Draw(image)
    sx = image.width / 1200.0
    sy = image.height / 1800.0

    colors = {
        "aisle": "#0B63B6",
        "column": "#07883D",
        "level": "#F57C00",
        "position": "#6A1B9A",
        "navy": "#075A9C",
    }

    def rect(x1, y1, x2, y2, fill):
        draw.rectangle((int(x1*sx), int(y1*sy), int(x2*sx), int(y2*sy)), fill=fill)

    def centered(text, box, fill, size, bold=True):
        x1, y1, x2, y2 = box
        font = _font(max(10, int(size * min(sx, sy))), bold=bold)
        bbox = draw.textbbox((0, 0), text, font=font)
        w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
        x = int(((x1+x2)/2)*sx - w/2)
        y = int(((y1+y2)/2)*sy - h/2)
        draw.text((x, y), text, font=font, fill=fill)

    # Banda superior sin logo ni marca.
    rect(55, 55, 1145, 150, colors["navy"])
    centered("UBICACIÓN DE ALMACÉN", (55, 55, 1145, 150), "white", 43)

    # Código completo segmentado por color.
    rect(55, 170, 905, 350, "white")
    parts = [
        (record.pls_aisle or "-", colors["aisle"]),
        (record.pls_column or "-", colors["column"]),
        (record.pls_level or "-", colors["level"]),
        (record.pls_position or "-", colors["position"]),
    ]
    font = _font(max(10, int(112 * min(sx, sy))), bold=True)
    widths = []
    for text, _color in parts:
        b = draw.textbbox((0, 0), text, font=font)
        widths.append(b[2]-b[0])
    gap = int(5*sx)
    total = sum(widths) + gap*(len(parts)-1)
    cursor = (int(55*sx)+int(905*sx))/2 - total/2
    y = int(190*sy)
    for (text, color), width in zip(parts, widths):
        draw.text((int(cursor), y), text, font=font, fill=color)
        cursor += width + gap

    # Bloques Pasillo / Columna / Nivel / Posición.
    blocks = [
        ((55, 610, 312, 890), colors["aisle"], "PASILLO", record.pls_aisle or "-"),
        ((330, 610, 587, 890), colors["column"], "COLUMNA", record.pls_column or "-"),
        ((605, 610, 862, 890), colors["level"], "NIVEL", record.pls_level or "-"),
        ((880, 610, 1137, 890), colors["position"], "POSICIÓN", record.pls_position or "-"),
    ]
    for box, color, title, value in blocks:
        rect(*box, color)
        centered(title, (box[0], box[1]+10, box[2], box[1]+78), "white", 27)
        centered(value, (box[0], box[1]+80, box[2], box[3]-8), "white", 74)

    # Pie visual limpio.
    rect(55, 1125, 1145, 1225, "#F3F6F9")
    centered("ORGANIZACIÓN HOY, EFICIENCIA SIEMPRE", (55, 1125, 1145, 1225), colors["navy"], 23)

    out = BytesIO()
    image.save(out, format="PNG")
    return base64.b64encode(out.getvalue())


def open_preview_wizard(record, *, label_type, title, report_xmlid, width, height, render_records=None):
    """Abre el modal de vista previa antes de imprimir."""
    record.ensure_one()
    records_to_render = render_records or record
    zpl_code = render_qweb_text(records_to_render, report_xmlid)
    if label_type == "location":
        preview_image = _location_color_preview(record, zpl_code)
    else:
        preview_image = labelary_multi_png(zpl_code, width, height)
    wizard = record.env["pls.zpl.label.preview.wizard"].create({
        "label_type": label_type,
        "source_model": record._name,
        "source_res_id": record.id,
        "source_name": record.display_name,
        "preview_image": preview_image,
        "zpl_code": zpl_code,
    })
    return {
        "name": title,
        "type": "ir.actions.act_window",
        "res_model": "pls.zpl.label.preview.wizard",
        "view_mode": "form",
        "res_id": wizard.id,
        "target": "new",
    }
