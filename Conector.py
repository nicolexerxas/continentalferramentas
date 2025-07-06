import requests

class FoccoAPI:
    def __init__(self, base_url: str, token: str):
        """
        Cliente HTTP para API REST do Focco ERP.
        :param base_url: URL base da API (ex.: https://api.foccoerp.com.br)
        :param token: Bearer Token gerado no Focco (programa FUTL0243)
        """
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

    def calculate_quote_tax(self, quote_payload: dict) -> dict:
        """
        POST /api/v1/cotacoes
        Envia a cotação do Odoo para o Focco calcular e adicionar impostos.
        Retorna o JSON da cotação com os valores tributários preenchidos.
        """
        url = f"{self.base_url}/api/v1/cotacoes"
        response = requests.post(url, json=quote_payload, headers=self.headers, timeout=10)
        response.raise_for_status()                  # dispara erro para códigos >=400
        return response.json()

    def send_sales_order(self, order_payload: dict) -> dict:
        """
        POST /api/v1/pedidos-venda
        Envia o pedido de venda confirmado no Odoo para faturamento e emissão de NF-e.
        Retorna o JSON com os dados do pedido, incluindo pedidoVendaId, invoiceId, status, itemsFaturados.
        """
        url = f"{self.base_url}/api/v1/pedidos-venda"
        response = requests.post(url, json=order_payload, headers=self.headers, timeout=10)
        response.raise_for_status()
        return response.json()

    def poll_invoices(self, pedido_venda_id: int) -> dict:
        """
        GET /api/v1/pedidos-venda/{pedidoVendaId}/invoices
        Consulta as notas/faturas geradas para um pedido de venda.
        - Se ainda não houver faturamento, retorna {} (HTTP 204 No Content).
        - Se houver, retorna o JSON com a lista de invoices.
        """
        url = f"{self.base_url}/api/v1/pedidos-venda/{pedido_venda_id}/invoices"
        response = requests.get(url, headers=self.headers, timeout=10)
        if response.status_code == 204:
            return {}
        response.raise_for_status()
        return response.json()

    def get_product_stock(self, product_code: str) -> float:
        """
        GET /api/v1/produtos/{codProduto}/saldo
        Consulta o saldo de estoque de um produto no Focco ERP.
        Retorna a soma dos saldos de todos os almoxarifados/filiais.
        """
        url = f"{self.base_url}/api/v1/produtos/{product_code}/saldo"
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        total = 0.0
        for item in data:
            # cada item geralmente tem campo "Saldo"
            saldo = item.get('Saldo') or item.get('saldo') or 0
            total += float(saldo)
        return total