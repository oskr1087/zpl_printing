from odoo import fields, models, _

from .zpl_preview_utils import open_preview_wizard


class StockPackage(models.Model):
    _inherit = "stock.package"

    zpl_operator_id = fields.Many2one(
        "res.users",
        string="Operador de etiqueta",
        default=lambda self: self.env.user,
        help="Operador responsable del empaque/etiqueta de trazabilidad.",
    )

    def _zpl_move_lines(self):
        self.ensure_one()
        return self.env["stock.move.line"].search(
            [("result_package_id", "=", self.id)],
            order="id",
        )

    def _zpl_picking(self):
        self.ensure_one()
        lines = self._zpl_move_lines()
        return lines[:1].picking_id

    def _zpl_sale_order(self):
        self.ensure_one()
        picking = self._zpl_picking()
        return picking.sale_id if picking and "sale_id" in picking._fields else self.env["sale.order"]

    def _zpl_package_sequence(self):
        self.ensure_one()
        picking = self._zpl_picking()
        if not picking:
            return (1, 1)
        package_ids = self.env["stock.move.line"].search([
            ("picking_id", "=", picking.id),
            ("result_package_id", "!=", False),
        ]).mapped("result_package_id")
        packages = package_ids.sorted(key=lambda p: p.id)
        total = len(packages) or 1
        try:
            current = list(packages.ids).index(self.id) + 1
        except ValueError:
            current = 1
        return current, total

    def _zpl_total_weight(self):
        self.ensure_one()
        total = 0.0
        for line in self._zpl_move_lines():
            total += (line.quantity or 0.0) * (line.product_id.weight or 0.0)
        return total

    def _zpl_primary_line(self):
        self.ensure_one()
        return self._zpl_move_lines()[:1]

    def _zpl_barcode_value(self):
        self.ensure_one()
        picking = self._zpl_picking()
        line = self._zpl_primary_line()
        sale = self._zpl_sale_order()
        parts = [
            sale.name if sale else "",
            self.name or "",
            line.lot_id.name if line and line.lot_id else "",
            picking.name if picking else "",
        ]
        return "-".join(filter(None, parts))


    def action_open_zpl_preview_traceability(self):
        self.ensure_one()
        return open_preview_wizard(
            self,
            label_type="traceability",
            title=_("Vista previa - Trazabilidad 4x3"),
            report_xmlid="pls_zpl_labels.action_report_zpl_traceability",
            width=4,
            height=3,
        )

    def action_print_zpl_traceability(self):
        self.ensure_one()
        return self.env.ref("pls_zpl_labels.action_report_zpl_traceability").report_action(self)
