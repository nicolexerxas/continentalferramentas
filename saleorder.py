from odoo import api, fields, models
import logging
from .focco_api import FoccoAPI

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    focco_order_id = fields.Char("Focco Order ID", readonly=True)
    focco_status = fields.Selection([
        ('pending', 'Pendente'),
        ('sent', 'Enviado'),
        ('invoiced_partial', 'Faturado Parcial'),
        ('invoiced_full', 'Faturado Total'),
        ('error', 'Erro')],
        default='pending')
    focco_invoiced = fields.Boolean("Recebido Faturamento", default=False)

    @api.model
    def _get_focco_client(self):
        IrConfig = self.env['ir.config_parameter'].sudo()
        return FoccoAPI(
            base_url=IrConfig.get_param('sale_focco.base_url'),
            token=IrConfig.get_param('sale_focco.token'),
        )

    def action_confirm(self):
        res = super().action_confirm()
        for order in self.filtered(lambda o: not o.focco_order_id):
            order._send_to_focco()
        return res

    def _build_focco_payload(self):
        # montar payload conforme De-Para (veja seção 6)
        # exemplo simplificado:
        lines = []
        for l in self.order_line:
            lines.append({
                "product": {
                    "catalogCode": "FoccoERP",
                    "catalogVersionNo": "1",
                    "productCode": l.product_id.default_code,
                    "productVersionNo": "1",
                    "netPrice": f"{l.price_unit:.4f}",
                    "qty": str(int(l.product_uom_qty)),
                    "productUomCode": l.product_uom.name,
                }
            })
        return {"salesOrder": {
            "orderDate": self.date_order.strftime("%Y-%m-%d"),
            "requestDate": self.confirmation_date.strftime("%Y-%m-%d"),
            "orderTypeCode": self.order_type_code,         # mapeado no De-Para
            "paymentTermsCode": self.payment_term_id.code, # idem
            "plantCode": self.warehouse_id.code,
            "currencyCode": self.pricelist_id.currency_id.name,
            "taxCode": self.tax_code,                      # mapeado
            "orderNoForeign": self.name,
            "organization": { "address": self._get_addresses() },
            "salesOrderLine": lines
        }}

    def _send_to_focco(self):
        client = self._get_focco_client()
        try:
            data = client.send_sales_order(self._build_focco_payload())
            so = data.get('salesOrder') or data
            self.write({
                'focco_order_id': so.get('pedidoVendaId'),
                'focco_status': 'sent',
            })
        except Exception as e:
            self.write({'focco_status': 'error'})
            _logger.exception("Erro ao enviar pedido %s", self.name)

    def update_focco_invoices(self):
        client = self._get_focco_client()
        for order in self.filtered(lambda o: o.focco_order_id and not o.focco_invoiced):
            invs = client.poll_invoices(int(order.focco_order_id))
            if invs:
                # parse e write status + linhas faturadas
                order.write({'focco_status': 'invoiced_full', 'focco_invoiced': True})