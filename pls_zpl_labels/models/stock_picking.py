from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .zpl_preview_utils import open_preview_wizard


class StockPicking(models.Model):
    _inherit = "stock.picking"

    pls_show_label_button = fields.Boolean(
        string="Mostrar impresión de etiquetas",
        compute="_compute_pls_show_label_button",
    )

    @api.depends("state", "picking_type_id.code")
    def _compute_pls_show_label_button(self):
        for picking in self:
            operation_code = picking.picking_type_id.code if picking.picking_type_id else False
            picking.pls_show_label_button = (
                picking.state == "done" and operation_code in ("incoming", "outgoing")
            )

    def _pls_operation_code(self):
        self.ensure_one()
        return self.picking_type_id.code if self.picking_type_id else self.picking_type_code

    def _pls_zpl_label_lines(self):
        self.ensure_one()
        return self.move_line_ids.filtered(
            lambda line: line.product_id and (line.quantity or 0.0) > 0
        ).sorted(key=lambda line: (line.product_id.display_name or "", line.id))

    def action_open_pls_zpl_labels_preview(self):
        self.ensure_one()
        if self.state != "done":
            raise UserError(_("Las etiquetas solo pueden imprimirse cuando la operación está validada."))
        operation_code = self._pls_operation_code()
        if operation_code not in ("incoming", "outgoing"):
            raise UserError(_("Este tipo de operación no tiene una etiqueta PLS configurada."))

        lines = self._pls_zpl_label_lines()
        if not lines:
            raise UserError(_("La operación no tiene líneas realizadas para imprimir."))

        if operation_code == "incoming":
            return open_preview_wizard(
                self,
                label_type="partial",
                title=_("Imprimir etiquetas - Bulto Parcial 4x2"),
                report_xmlid="pls_zpl_labels.action_report_zpl_partial_package",
                width=4,
                height=2,
                render_records=lines,
            )

        return open_preview_wizard(
            self,
            label_type="traceability",
            title=_("Imprimir etiquetas - Trazabilidad del Pedido 4x3"),
            report_xmlid="pls_zpl_labels.action_report_zpl_traceability",
            width=4,
            height=3,
            render_records=lines,
        )

    def action_print_pls_zpl_labels(self):
        self.ensure_one()
        if self.state != "done":
            raise UserError(_("Las etiquetas solo pueden imprimirse cuando la operación está validada."))

        lines = self._pls_zpl_label_lines()
        if not lines:
            raise UserError(_("La operación no tiene líneas realizadas para imprimir."))

        operation_code = self._pls_operation_code()
        if operation_code == "incoming":
            report = self.env.ref("pls_zpl_labels.action_report_zpl_partial_package")
        elif operation_code == "outgoing":
            report = self.env.ref("pls_zpl_labels.action_report_zpl_traceability")
        else:
            raise UserError(_("Este tipo de operación no tiene una etiqueta PLS configurada."))
        return report.report_action(lines)
