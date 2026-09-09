from odoo import _, fields, models
from odoo.exceptions import UserError


class PlsZplLabelPreviewWizard(models.TransientModel):
    _name = "pls.zpl.label.preview.wizard"
    _description = "Vista previa de etiqueta ZPL PLS"

    label_type = fields.Selection(
        [
            ("partial", "Bulto Parcial 4x2"),
            ("location", "Ubicación 4x6"),
            ("traceability", "Trazabilidad 4x3"),
        ],
        string="Formato",
        readonly=True,
        required=True,
    )
    source_model = fields.Char(string="Modelo origen", readonly=True, required=True)
    source_res_id = fields.Integer(string="ID origen", readonly=True, required=True)
    source_name = fields.Char(string="Documento", readonly=True)
    preview_image = fields.Binary(string="Vista previa", readonly=True)
    zpl_code = fields.Text(string="Código ZPL", readonly=True)

    def action_print_zpl(self):
        self.ensure_one()

        if self.label_type == "location":
            if self.source_model != "stock.location":
                raise UserError(_("No se pudo determinar el formato ZPL a imprimir."))
            record = self.env["stock.location"].browse(self.source_res_id).exists()
            if not record:
                raise UserError(_("El registro origen ya no existe."))
            return self.env.ref("pls_zpl_labels.action_report_zpl_location").report_action(record)

        if self.source_model != "stock.picking":
            raise UserError(_("No se pudo determinar el documento de inventario a imprimir."))

        picking = self.env["stock.picking"].browse(self.source_res_id).exists()
        if not picking:
            raise UserError(_("La operación de inventario ya no existe."))
        return picking.action_print_pls_zpl_labels()
