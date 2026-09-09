from odoo import api, fields, models, _

from .zpl_preview_utils import open_preview_wizard


class StockLocation(models.Model):
    _inherit = "stock.location"

    pls_aisle = fields.Char(string="Pasillo")
    pls_column = fields.Char(string="Columna")
    pls_level = fields.Char(string="Nivel")
    pls_position = fields.Char(string="Posición")

    def _pls_build_location_name(self, values=None):
        """Pasillo + Columna + Nivel + Posición, por ejemplo A1C1N501."""
        self.ensure_one()
        values = values or {}
        parts = [
            values.get("pls_aisle", self.pls_aisle),
            values.get("pls_column", self.pls_column),
            values.get("pls_level", self.pls_level),
            values.get("pls_position", self.pls_position),
        ]
        return "".join((part or "").strip().upper() for part in parts)

    @api.onchange("pls_aisle", "pls_column", "pls_level", "pls_position")
    def _onchange_pls_structure(self):
        """Muestra el código final mientras el usuario captura la estructura."""
        for location in self:
            location.name = location._pls_build_location_name()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if any(key in vals for key in ("pls_aisle", "pls_column", "pls_level", "pls_position")):
                parts = [
                    vals.get("pls_aisle", ""),
                    vals.get("pls_column", ""),
                    vals.get("pls_level", ""),
                    vals.get("pls_position", ""),
                ]
                generated_name = "".join((part or "").strip().upper() for part in parts)
                if generated_name:
                    vals["name"] = generated_name
        return super().create(vals_list)

    def write(self, vals):
        structure_fields = {"pls_aisle", "pls_column", "pls_level", "pls_position"}
        if not structure_fields.intersection(vals):
            return super().write(vals)

        for location in self:
            local_vals = dict(vals)
            generated_name = location._pls_build_location_name(local_vals)
            if generated_name:
                local_vals["name"] = generated_name
            super(StockLocation, location).write(local_vals)
        return True

    def action_open_zpl_preview_location(self):
        self.ensure_one()
        return open_preview_wizard(
            self,
            label_type="location",
            title=_("Imprimir etiqueta - Ubicación 4x6"),
            report_xmlid="pls_zpl_labels.action_report_zpl_location",
            width=4,
            height=6,
        )

    def action_print_zpl_location(self):
        self.ensure_one()
        return self.env.ref("pls_zpl_labels.action_report_zpl_location").report_action(self)
