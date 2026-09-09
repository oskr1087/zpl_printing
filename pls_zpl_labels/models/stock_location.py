from odoo import api, fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    pls_aisle = fields.Char(string="Pasillo")
    pls_column = fields.Char(string="Columna")
    pls_level = fields.Char(string="Nivel")
    pls_position = fields.Char(string="Posición")

    def _pls_build_location_name(self, values=None):
        """Construye el nombre de ubicación con Pasillo + Columna + Nivel + Posición.

        No se agregan separadores porque el formato requerido es, por ejemplo, A1C1N501.
        """
        self.ensure_one()
        values = values or {}
        parts = [
            values.get("pls_aisle", self.pls_aisle),
            values.get("pls_column", self.pls_column),
            values.get("pls_level", self.pls_level),
            values.get("pls_position", self.pls_position),
        ]
        return "".join((part or "").strip().upper() for part in parts)

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

        # Cada ubicación puede tener una combinación distinta, por lo que se actualiza
        # registro a registro evitando recursividad.
        for location in self:
            local_vals = dict(vals)
            generated_name = location._pls_build_location_name(local_vals)
            if generated_name:
                local_vals["name"] = generated_name
            super(StockLocation, location).write(local_vals)
        return True
