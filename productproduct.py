from odoo import api, fields, models
from .focco_api import FoccoAPI
import logging

_logger = logging.getLogger(__name__)

class ProductProduct(models.Model):
    _inherit = "product.product"

    focco_qty_onhand = fields.Float("Qtd. em mãos (Focco)", readonly=True)

    def update_focco_stock(self):
        client = FoccoAPI(
            base_url=self.env['ir.config_parameter'].sudo().get_param('sale_focco.base_url'),
            token=self.env['ir.config_parameter'].sudo().get_param('sale_focco.token'),
        )
        for prod in self:
            if not prod.default_code:
                continue
            try:
                total = client.get_product_stock(prod.default_code)
                prod.write({'focco_qty_onhand': total})
            except Exception:
                _logger.exception("Erro ao atualizar estoque %s", prod.default_code)