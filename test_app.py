import unittest

import app as sistema


class TesteSistemaRestaurante(unittest.TestCase):
    def setUp(self):
        self.cliente = sistema.app.test_client()

    def test_pagina_inicial_abre(self):
        resposta = self.cliente.get("/")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"Sabor da Casa", resposta.data)

    def test_fluxo_completo_de_venda(self):
        resposta = self.cliente.post("/api/pedidos", json={
            "mesa": 1,
            "itens": [{"nome": "Pudim", "quantidade": 2}]
        })
        self.assertEqual(resposta.status_code, 201)

        numero = resposta.get_json()["pedido"]["numero"]
        resposta = self.cliente.post(
            f"/api/pedidos/{numero}/finalizar",
            json={"forma_pagamento": "PIX"}
        )
        self.assertEqual(resposta.status_code, 200)

        dados = self.cliente.get("/api/dados").get_json()
        self.assertEqual(dados["caixa"]["total_vendido"], 24.0)
        self.assertEqual(dados["caixa"]["quantidade_vendas"], 1)


if __name__ == "__main__":
    unittest.main()
