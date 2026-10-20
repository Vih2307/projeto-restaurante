import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from werkzeug.security import generate_password_hash
import app as sistema
import usuario as arquivo_usuarios
from usuario import Usuario, carregar_usuarios, salvar_usuarios
from caixa import Caixa
from estoque import Estoque
from mesa import Mesa
from carrinho import Carrinho


class TesteSistemaRestaurante(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.arquivo_anterior = arquivo_usuarios.ARQUIVO_USUARIOS
        arquivo_usuarios.ARQUIVO_USUARIOS = Path(self.pasta.name) / "usuarios.json"
        self.addCleanup(self.restaurar_arquivo)
        sistema.app.config["TESTING"] = True
        sistema.usuarios = [Usuario("Kennedy", "teste@exemplo.com", generate_password_hash("Senha12345"))]
        sistema.tentativas_login = {}
        sistema.mesas = [Mesa("Livre", numero, False) for numero in range(1, 9)]
        sistema.pedidos = []
        sistema.caixa = Caixa()
        sistema.estoque = Estoque()
        sistema.numero_pedido = 1
        sistema.iniciar_sistema()
        salvar_usuarios(sistema.usuarios)
        self.cliente = sistema.app.test_client()
        self.cliente.post("/api/login", json={"email": "teste@exemplo.com", "senha": "Senha12345"})
        with self.cliente.session_transaction() as sessao:
            self.headers = {"X-CSRF-Token": sessao["token"]}

    def restaurar_arquivo(self):
        arquivo_usuarios.ARQUIVO_USUARIOS = self.arquivo_anterior

    def enviar(self, rota, dados):
        return self.cliente.post(rota, json=dados, headers=self.headers)

    def criar_pedido(self):
        return self.enviar("/api/pedidos", {"mesa": 1, "itens": [{"nome": "Pudim", "quantidade": 2}]})

    def solicitar_codigo(self):
        with patch("app.enviar_codigo") as envio:
            resposta = self.enviar("/api/recuperar-senha", {"email": "teste@exemplo.com"})
            self.assertEqual(resposta.status_code, 200)
            return envio.call_args.args[1]

    def redefinir(self, codigo):
        return self.enviar("/api/alterar-senha", {
            "email": "teste@exemplo.com", "codigo": codigo,
            "senha": "NovaSenha123", "confirmacao": "NovaSenha123"
        })

    def test_paginas_e_acesso(self):
        self.assertIn(b"Sabor da Casa", self.cliente.get("/").data)
        anonimo = sistema.app.test_client()
        self.assertEqual(anonimo.get("/").status_code, 302)
        self.assertEqual(anonimo.get("/api/dados").status_code, 401)
        self.assertEqual(anonimo.get("/login").status_code, 200)
        self.assertEqual(self.cliente.post("/api/pedidos", json={}).status_code, 403)
        self.assertEqual(self.enviar("/api/sair", {}).status_code, 200)
        self.assertEqual(self.cliente.get("/api/dados").status_code, 401)

    def test_fluxo_completo_de_venda(self):
        resposta = self.criar_pedido()
        self.assertEqual(resposta.status_code, 201)
        numero = resposta.json["pedido"]["numero"]
        rota = f"/api/pedidos/{numero}/finalizar"
        self.assertEqual(self.enviar(rota, {"forma_pagamento": "PIX"}).status_code, 200)
        self.assertEqual(self.enviar(rota, {"forma_pagamento": "PIX"}).status_code, 404)
        dados = self.cliente.get("/api/dados").json
        self.assertEqual(dados["caixa"]["total_vendido"], 24)
        self.assertEqual(sistema.estoque.produtos_prontos["Pudim"]["quantidade"], 13)

    def test_itens_repetidos_e_estoque(self):
        resposta = self.enviar("/api/pedidos", {"mesa": 1, "itens": [
            {"nome": "Pudim", "quantidade": 10}, {"nome": "Pudim", "quantidade": 10}
        ]})
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(sistema.estoque.produtos_prontos["Pudim"]["quantidade"], 15)
        self.assertEqual(sistema.pedidos, [])
        resposta = self.enviar("/api/pedidos", {"mesa": 1, "itens": [
            {"nome": "Pudim", "quantidade": 2}, {"nome": "Pudim", "quantidade": 3}
        ]})
        self.assertEqual(resposta.json["pedido"]["total"], 60)

    def test_entradas_invalidas(self):
        for quantidade in [True, 1.5, "1.5", 0, -1, None, {}, 10001]:
            resposta = self.enviar("/api/pedidos", {"mesa": 1, "itens": [{"nome": "Pudim", "quantidade": quantidade}]})
            self.assertEqual(resposta.status_code, 400)
        for itens in [None, {}, [None], ["Pudim"], []]:
            resposta = self.enviar("/api/pedidos", {"mesa": 1, "itens": itens})
            self.assertEqual(resposta.status_code, 400)
        self.assertEqual(self.cliente.post("/api/pedidos", json=[], headers=self.headers).status_code, 400)
        self.assertEqual(self.enviar("/api/estoque/entrada", {"nome": [], "quantidade": 2}).status_code, 400)

    def test_cancelar(self):
        self.criar_pedido()
        self.assertEqual(self.enviar("/api/pedidos/1/cancelar", {"motivo": "Cliente desistiu"}).status_code, 200)
        self.assertEqual(sistema.estoque.produtos_prontos["Pudim"]["quantidade"], 15)
        self.assertEqual(sistema.mesas[0].status, "Livre")
        self.assertEqual(self.enviar("/api/pedidos/1/cancelar", {"motivo": "Cliente desistiu"}).status_code, 400)
        self.assertEqual(self.enviar("/api/pedidos/1/finalizar", {"forma_pagamento": "PIX"}).status_code, 404)

    def test_status(self):
        self.criar_pedido()
        self.assertEqual(self.enviar("/api/pedidos/1/status", {"status": "Entregue"}).status_code, 400)
        self.assertEqual(self.enviar("/api/pedidos/1/status", {"status": "Pronto"}).status_code, 200)
        self.assertEqual(self.enviar("/api/pedidos/1/status", {"status": "Entregue"}).status_code, 200)

    def test_codigo_e_senha_nova(self):
        codigo = self.solicitar_codigo()
        self.assertEqual(len(codigo), 6)
        self.assertNotEqual(sistema.usuarios[0].codigo, codigo)
        self.assertEqual(self.redefinir(codigo).status_code, 200)
        self.assertEqual(self.redefinir(codigo).status_code, 400)
        self.assertEqual(self.cliente.get("/api/dados").status_code, 401)
        self.assertEqual(self.cliente.post("/api/login", json={"email": "teste@exemplo.com", "senha": "Senha12345"}).status_code, 401)
        self.assertEqual(self.cliente.post("/api/login", json={"email": "teste@exemplo.com", "senha": "NovaSenha123"}).status_code, 200)
        recarregados = carregar_usuarios()
        self.assertTrue(recarregados[0].verificar_senha("NovaSenha123"))
        self.assertNotEqual(recarregados[0].senha, "NovaSenha123")

    def test_codigo_expirado(self):
        codigo = self.solicitar_codigo()
        sistema.usuarios[0].validade_codigo = time.time() - 1
        self.assertEqual(self.redefinir(codigo).status_code, 400)

    def test_limite_codigo(self):
        codigo = self.solicitar_codigo()
        incorreto = "000000" if codigo != "000000" else "111111"
        for tentativa in range(5):
            self.assertEqual(self.redefinir(incorreto).status_code, 400)
        self.assertEqual(self.redefinir(codigo).status_code, 400)
        with patch("app.enviar_codigo") as envio:
            self.enviar("/api/recuperar-senha", {"email": "teste@exemplo.com"})
            envio.assert_not_called()

    def test_novo_codigo_substitui_anterior(self):
        with patch("app.secrets.randbelow", return_value=123456):
            antigo = self.solicitar_codigo()
        sistema.usuarios[0].ultimo_envio = 0
        with patch("app.secrets.randbelow", return_value=654321):
            novo = self.solicitar_codigo()
        self.assertEqual(self.redefinir(antigo).status_code, 400)
        self.assertEqual(self.redefinir(novo).status_code, 200)

    def test_erro_smtp_e_email_desconhecido(self):
        with patch("app.enviar_codigo", side_effect=OSError("Falha SMTP")):
            conhecido = self.enviar("/api/recuperar-senha", {"email": "teste@exemplo.com"})
        desconhecido = self.enviar("/api/recuperar-senha", {"email": "ausente@exemplo.com"})
        self.assertEqual(conhecido.json, desconhecido.json)
        self.assertEqual(sistema.usuarios[0].codigo, "")

    def test_limite_login(self):
        for tentativa in range(9):
            self.cliente.post("/api/login", json={"email": "teste@exemplo.com", "senha": "errada"})
        self.assertEqual(self.cliente.post("/api/login", json={}).status_code, 429)

    def test_confirmacao_de_senha(self):
        codigo = self.solicitar_codigo()
        resposta = self.enviar("/api/alterar-senha", {"email": "teste@exemplo.com", "codigo": codigo, "senha": "NovaSenha123", "confirmacao": "Diferente123"})
        self.assertEqual(resposta.status_code, 400)
        self.assertTrue(sistema.usuarios[0].verificar_senha("Senha12345"))

    def test_carrinho(self):
        carrinho = Carrinho()
        carrinho.adicionar_item("Água", 5, 2)
        carrinho.adicionar_item("Água", 5, 1)
        self.assertEqual(carrinho.calcular_total(), 15)
        carrinho.escolher_pagamento("PIX")
        self.assertEqual(carrinho.finalizar_compra(), 15)
        with self.assertRaises(ValueError):
            carrinho.finalizar_compra()
        self.criar_pedido()
        self.assertIsInstance(sistema.pedidos[0], Carrinho)


if __name__ == "__main__":
    unittest.main()
