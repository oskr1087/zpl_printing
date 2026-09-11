import base64
from io import BytesIO

import requests
from PIL import Image

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



def open_preview_wizard(record, *, label_type, title, report_xmlid, width, height, render_records=None):
    """Abre el modal de vista previa antes de imprimir."""
    record.ensure_one()
    records_to_render = render_records or record
    zpl_code = render_qweb_text(records_to_render, report_xmlid)
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
