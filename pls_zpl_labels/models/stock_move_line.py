from odoo import api, fields, models, _

from .zpl_preview_utils import open_preview_wizard


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    zpl_opening_date = fields.Date(
        string="Fecha de apertura",
        help="Fecha de apertura o generación del bulto parcial para su etiqueta ZPL.",
    )
    zpl_expiration_date = fields.Date(
        string="Vencimiento para etiqueta",
        help="Fecha de vencimiento usada solo cuando el lote no tiene una fecha de caducidad configurada.",
    )
    zpl_operator_id = fields.Many2one(
        "res.users",
        string="Operador de etiqueta",
        default=lambda self: self.env.user,
        help="Operador responsable de la impresión de la etiqueta.",
    )
    zpl_picking_type_code = fields.Selection(
        related="picking_id.picking_type_code",
        string="Tipo de operación",
        readonly=True,
    )

    def _zpl_expiration_date_text(self):
        self.ensure_one()
        lot = self.lot_id
        expiration_date = False
        if lot:
            for field_name in ("expiration_date", "use_date", "life_date"):
                if field_name in lot._fields and lot[field_name]:
                    expiration_date = lot[field_name]
                    break
        if not expiration_date and self.zpl_expiration_date:
            expiration_date = self.zpl_expiration_date
        return (
            fields.Datetime.to_datetime(expiration_date).strftime("%d/%m/%Y")
            if expiration_date
            else ""
        )

    def _zpl_opening_date_text(self):
        self.ensure_one()
        opening_date = self.zpl_opening_date
        if not opening_date and self.picking_id.date_done:
            opening_date = fields.Datetime.to_datetime(self.picking_id.date_done).date()
        return (
            fields.Date.to_date(opening_date).strftime("%d/%m/%Y")
            if opening_date
            else ""
        )

    def _zpl_partial_barcode_value(self):
        self.ensure_one()
        sku = self.product_id.default_code or self.product_id.barcode or str(self.product_id.id)
        lot = self.lot_id.name or self.lot_name or "SINLOTE"
        opening_date = self.zpl_opening_date
        if not opening_date and self.picking_id.date_done:
            opening_date = fields.Datetime.to_datetime(self.picking_id.date_done).date()
        opening = (
            fields.Date.to_date(opening_date).strftime("%d%m%Y")
            if opening_date
            else ""
        )
        qty = "%g" % (self.quantity or 0.0)
        return "-".join(filter(None, ["PP", sku, lot, opening, qty]))

    def _zpl_sale_order(self):
        self.ensure_one()
        picking = self.picking_id
        if not picking:
            return self.env["sale.order"]
        if "sale_id" in picking._fields and picking.sale_id:
            return picking.sale_id
        if picking.origin:
            return self.env["sale.order"].search([("name", "=", picking.origin)], limit=1)
        return self.env["sale.order"]

    def _zpl_delivery_destination(self):
        self.ensure_one()
        partner = self.picking_id.partner_id
        if not partner:
            return ""
        values = [partner.street, partner.street2, partner.city, partner.state_id.name, partner.country_id.name]
        return ", ".join(value for value in values if value)

    def _zpl_delivery_sequence(self):
        """Secuencia de etiqueta dentro de la entrega.

        Si la línea pertenece a un paquete se numera por paquete. Si no existe
        paquete, se numera por línea para mantener el requisito de una etiqueta
        por cada línea de movimiento de entrega.
        """
        self.ensure_one()
        picking = self.picking_id
        if not picking:
            return (1, 1)

        lines = picking.move_line_ids.filtered(lambda line: line.quantity or line.product_id)
        if not lines:
            return (1, 1)

        package = self.result_package_id or self.outermost_result_package_id
        if package:
            packages = []
            for line in lines:
                current = line.result_package_id or line.outermost_result_package_id
                if current and current not in packages:
                    packages.append(current)
            if package in packages:
                return (packages.index(package) + 1, len(packages))

        ordered = lines.sorted(key=lambda line: line.id)
        return ((list(ordered).index(self) + 1) if self in ordered else 1, len(ordered))

    def _zpl_delivery_weight(self):
        self.ensure_one()
        package = self.result_package_id or self.outermost_result_package_id
        if package:
            for field_name in ("shipping_weight", "weight"):
                if field_name in package._fields and package[field_name]:
                    return package[field_name]
        return (self.product_id.weight or 0.0) * (self.quantity or 0.0)

    def _zpl_delivery_barcode_value(self):
        self.ensure_one()
        sale = self._zpl_sale_order()
        seq, _total = self._zpl_delivery_sequence()
        lot = self.lot_id.name or self.lot_name or "SINLOTE"
        order = sale.name if sale else (self.picking_id.origin or self.picking_id.name or "")
        return "%s-%03d-%s" % (order.replace("/", ""), seq, lot)

    def _zpl_operator_name(self):
        self.ensure_one()
        # En recepciones ya validadas muchas líneas pueden haber sido creadas
        # por procesos automáticos. Priorizamos el responsable del picking.
        return (
            (self.picking_id.user_id.name if self.picking_id and self.picking_id.user_id else "")
            or (self.env.user.name if self.env.user else "")
            or self.zpl_operator_id.name
            or (self.write_uid.name if self.write_uid else "")
        )

    def _zpl_quantity_text(self):
        self.ensure_one()
        return "%g %s" % ((self.quantity or 0.0), (self.product_uom_id.name or ""))

    def action_open_zpl_preview_partial(self):
        self.ensure_one()
        return open_preview_wizard(
            self,
            label_type="partial",
            title=_("Imprimir etiqueta - Bulto Parcial 4x2"),
            report_xmlid="pls_zpl_labels.action_report_zpl_partial_package",
            width=4,
            height=2,
        )

    def action_open_zpl_preview_traceability(self):
        self.ensure_one()
        return open_preview_wizard(
            self,
            label_type="traceability",
            title=_("Imprimir etiqueta - Trazabilidad del Pedido 4x3"),
            report_xmlid="pls_zpl_labels.action_report_zpl_traceability",
            width=4,
            height=3,
        )

    def action_print_zpl_partial(self):
        self.ensure_one()
        return self.env.ref("pls_zpl_labels.action_report_zpl_partial_package").report_action(self)

    def action_print_zpl_traceability(self):
        self.ensure_one()
        return self.env.ref("pls_zpl_labels.action_report_zpl_traceability").report_action(self)
