from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    zpl_opening_date = fields.Date(
        string="Fecha de apertura",
        help="Fecha de apertura o generación del bulto parcial para su etiqueta ZPL.",
    )
    zpl_operator_id = fields.Many2one(
        "res.users",
        string="Operador de etiqueta",
        default=lambda self: self.env.user,
        help="Operador responsable del bulto parcial.",
    )

    def _zpl_expiration_date_text(self):
        self.ensure_one()
        expiration_date = self.lot_id.expiration_date if self.lot_id else False
        return fields.Datetime.to_datetime(expiration_date).strftime("%d/%m/%Y") if expiration_date else ""

    def _zpl_opening_date_text(self):
        self.ensure_one()
        return fields.Date.to_date(self.zpl_opening_date).strftime("%d/%m/%Y") if self.zpl_opening_date else ""

    def _zpl_partial_barcode_value(self):
        self.ensure_one()
        sku = self.product_id.default_code or self.product_id.barcode or str(self.product_id.id)
        lot = self.lot_id.name or "SINLOTE"
        opening = fields.Date.to_date(self.zpl_opening_date).strftime("%d%m%Y") if self.zpl_opening_date else ""
        qty = "%g" % (self.quantity or 0.0)
        return "-".join(filter(None, ["PP", sku, lot, opening, qty]))
