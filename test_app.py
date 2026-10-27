import time
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import app as sistema
import autenticacao as modulo_autenticacao
import banco as modulo_banco
import cadastrar_usuario as modulo_cadastro
from autenticacao import ErroAutenticacao
from banco import BancoErro
from caixa import Caixa
from carrinho import Carrinho
from estoque import Estoque
from mesa import Mesa
from usuario import email_valido, nome_valido, senha_valida


class BancoFalso:
    """Troca o Neon por um dicionário em memória nos testes."""

    def __init__(self):
        self.usuarios = {
            "uid-1": {"id": 1, "firebase_uid": "uid-1", "nome": "Kennedy Fernando", "email": "teste@exemplo.com", "ativo": True}
        }
        self.recuperacoes_liberadas = True
        self.fora_do_ar = False
        self.logins = []

    def _conferir(self):
        if self.fora_do_ar:
            raise BancoErro("Neon fora do ar")

    def buscar_usuario_por_uid(self, uid):
        self._conferir()
        return self.usuarios.get(uid)

    def buscar_usuario_por_email(self, email):
        self._conferir()
        return next((u for u in self.usuarios.values() if u["email"] == email), None)

    def criar_usuario(self, uid, nome, email):
        self._conferir()
        self.usuarios[uid] = {"id": len(self.usuarios) + 1, "firebase_uid": uid, "nome": nome, "email": email, "ativo": True}

    def registrar_login(self, uid):
        self._conferir()
        self.logins.append(uid)

    def reservar_envio_recuperacao(self, email, intervalo_segundos=60):
        self._conferir()
        usuario = self.buscar_usuario_por_email(email)
        return bool(usuario and usuario["ativo"] and self.recuperacoes_liberadas)


class AutenticacaoFalsa:
    """Troca o Firebase por contas em memória nos testes."""

    def __init__(self):
        self.contas = {"teste@exemplo.com": {"uid": "uid-1", "senha": "Senha12345"}}
        self.relogio = 1000
        self.valido_apos = 0
        self.desativada = False
        self.indisponivel = False
        self.emails_enviados = []
        self.criadas = []
        self.removidas = []

    def entrar(self, email, senha):
        if self.indisponivel:
            raise ErroAutenticacao("indisponivel", "Firebase fora do ar")
        conta = self.contas.get(email)
        if conta is None or conta["senha"] != senha:
            raise ErroAutenticacao("credenciais", "E-mail ou senha incorretos.")
        self.relogio += 1
        return {"uid": conta["uid"], "email": email, "iat": self.relogio}

    def enviar_recuperacao(self, email):
        if self.indisponivel:
            raise ErroAutenticacao("indisponivel", "Firebase fora do ar")
        self.emails_enviados.append(email)

    def conta_ainda_valida(self, uid, iat):
        if self.indisponivel:
            raise ErroAutenticacao("indisponivel", "Firebase fora do ar")
        return not self.desativada and iat >= self.valido_apos

    def redefinir_senha(self, email, nova_senha):
        """Simula o que o Firebase faz quando a pessoa conclui o link do e-mail."""
        self.contas[email]["senha"] = nova_senha
        self.relogio += 1
        self.valido_apos = self.relogio

    def buscar_conta_por_email(self, email):
        conta = self.contas.get(email)
        return SimpleNamespace(uid=conta["uid"]) if conta else None

    def criar_conta(self, email, senha, nome):
        uid = "uid-" + str(len(self.contas) + 1)
        self.contas[email] = {"uid": uid, "senha": senha}
        self.criadas.append(uid)
        return uid

    def remover_conta(self, uid):
        self.removidas.append(uid)


class TesteSistemaRestaurante(unittest.TestCase):
    def setUp(self):
        self.banco = BancoFalso()
        self.firebase = AutenticacaoFalsa()
        self.banco_real = sistema.banco
        self.autenticacao_real = sistema.autenticacao
        sistema.banco = self.banco
        sistema.autenticacao = self.firebase
        self.addCleanup(self.restaurar)

        sistema.app.config["TESTING"] = True
        sistema.tentativas_login = {}
        sistema.tentativas_recuperacao = {}
        sistema.mesas = [Mesa("Livre", numero, False) for numero in range(1, 9)]
        sistema.pedidos = []
        sistema.caixa = Caixa()
        sistema.estoque = Estoque()
        sistema.numero_pedido = 1
        sistema.iniciar_sistema()
        self.cliente = sistema.app.test_client()
        self.cliente.post("/api/login", json={"email": "teste@exemplo.com", "senha": "Senha12345"})
        with self.cliente.session_transaction() as sessao:
            self.headers = {"X-CSRF-Token": sessao["token"]}

    def restaurar(self):
        sistema.banco = self.banco_real
        sistema.autenticacao = self.autenticacao_real

    def enviar(self, rota, dados):
        return self.cliente.post(rota, json=dados, headers=self.headers)

    def criar_pedido(self):
        return self.enviar("/api/pedidos", {"mesa": 1, "itens": [{"nome": "Pudim", "quantidade": 2}]})

    def logar(self, email="teste@exemplo.com", senha="Senha12345"):
        return sistema.app.test_client().post("/api/login", json={"email": email, "senha": senha})

    def forcar_conferencia(self):
        """Faz a próxima requisição conferir a sessão de novo no Firebase e no Neon."""
        with self.cliente.session_transaction() as sessao:
            sessao["tentou_em"] = 0

    # ---------- acesso ----------

    def test_paginas_e_acesso(self):
        pagina = self.cliente.get("/").data
        self.assertIn(b"Restaurante BKV", pagina)
        self.assertIn(b'data-nome="Kennedy Fernando"', pagina)
        anonimo = sistema.app.test_client()
        self.assertEqual(anonimo.get("/").status_code, 302)
        self.assertEqual(anonimo.get("/api/dados").status_code, 401)
        self.assertEqual(anonimo.get("/login").status_code, 200)
        self.assertEqual(self.cliente.post("/api/pedidos", json={}).status_code, 403)
        self.assertEqual(self.enviar("/api/sair", {}).status_code, 200)
        self.assertEqual(self.cliente.get("/api/dados").status_code, 401)

    def test_login_registra_horario_no_banco(self):
        self.assertEqual(self.banco.logins, ["uid-1"])

    def test_login_com_dados_incorretos(self):
        errada = self.logar(senha="Errada12345")
        desconhecido = self.logar(email="ausente@exemplo.com")
        self.assertEqual(errada.status_code, 401)
        self.assertEqual(errada.json, desconhecido.json)
        self.assertEqual(self.logar(email="sem-arroba").status_code, 401)
        self.assertEqual(self.logar(senha="").status_code, 401)

    def test_conta_do_firebase_sem_permissao_no_neon(self):
        self.firebase.contas["novo@exemplo.com"] = {"uid": "uid-novo", "senha": "Senha12345"}
        resposta = self.logar(email="novo@exemplo.com")
        self.assertEqual(resposta.status_code, 403)
        self.banco.usuarios["uid-novo"] = {"id": 2, "firebase_uid": "uid-novo", "nome": "Novo", "email": "novo@exemplo.com", "ativo": False}
        self.assertEqual(self.logar(email="novo@exemplo.com").status_code, 403)
        self.banco.usuarios["uid-novo"]["ativo"] = True
        self.assertEqual(self.logar(email="novo@exemplo.com").status_code, 200)

    def test_falhas_dos_servicos_no_login(self):
        self.firebase.indisponivel = True
        self.assertEqual(self.logar().status_code, 503)
        self.firebase.indisponivel = False
        self.banco.fora_do_ar = True
        self.assertEqual(self.logar().status_code, 503)
        self.banco.fora_do_ar = False
        with patch.object(self.firebase, "entrar", side_effect=ErroAutenticacao("configuracao", "chave errada")):
            resposta = self.logar()
        self.assertEqual(resposta.status_code, 503)
        self.assertNotIn("chave errada", resposta.get_data(as_text=True))
        with patch.object(self.firebase, "entrar", side_effect=ErroAutenticacao("desativada", "x")):
            self.assertEqual(self.logar().status_code, 403)
        with patch.object(self.firebase, "entrar", side_effect=ErroAutenticacao("muitas_tentativas", "x")):
            self.assertEqual(self.logar().status_code, 429)

    def test_limite_login(self):
        for tentativa in range(9):
            self.cliente.post("/api/login", json={"email": "teste@exemplo.com", "senha": "errada"})
        self.assertEqual(self.cliente.post("/api/login", json={}).status_code, 429)

    # ---------- sessão conferida no Firebase e no Neon ----------

    def test_sessao_cai_depois_de_redefinir_a_senha(self):
        self.firebase.redefinir_senha("teste@exemplo.com", "NovaSenha123")
        # Antes da próxima conferência periódica, a sessão ainda funciona.
        self.assertEqual(self.cliente.get("/api/dados").status_code, 200)
        self.forcar_conferencia()
        self.assertEqual(self.cliente.get("/api/dados").status_code, 401)
        self.assertEqual(self.logar(senha="Senha12345").status_code, 401)
        self.assertEqual(self.logar(senha="NovaSenha123").status_code, 200)

    def test_sessao_cai_se_usuario_for_desativado_ou_removido(self):
        self.banco.usuarios["uid-1"]["ativo"] = False
        self.forcar_conferencia()
        self.assertEqual(self.cliente.get("/api/dados").status_code, 401)

        self.banco.usuarios["uid-1"]["ativo"] = True
        cliente = sistema.app.test_client()
        cliente.post("/api/login", json={"email": "teste@exemplo.com", "senha": "Senha12345"})
        self.firebase.desativada = True
        with cliente.session_transaction() as sessao:
            sessao["tentou_em"] = 0
        self.assertEqual(cliente.get("/api/dados").status_code, 401)

    def test_servicos_fora_do_ar_nao_derrubam_a_sessao_de_imediato(self):
        self.firebase.indisponivel = True
        self.forcar_conferencia()
        self.assertEqual(self.cliente.get("/api/dados").status_code, 200)
        self.banco.fora_do_ar = True
        self.forcar_conferencia()
        self.assertEqual(self.cliente.get("/api/dados").status_code, 200)
        with self.cliente.session_transaction() as sessao:
            sessao["tentou_em"] = 0
            sessao["verificado_em"] = time.time() - sistema.TOLERANCIA_FALHA - 1
        self.assertEqual(self.cliente.get("/api/dados").status_code, 401)

    # ---------- esqueci minha senha ----------

    def test_recuperacao_envia_email_pelo_firebase(self):
        resposta = self.cliente.post("/api/recuperar-senha", json={"email": "Teste@Exemplo.com"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(self.firebase.emails_enviados, ["teste@exemplo.com"])

    def test_recuperacao_nao_revela_quem_esta_cadastrado(self):
        conhecido = self.cliente.post("/api/recuperar-senha", json={"email": "teste@exemplo.com"})
        desconhecido = self.cliente.post("/api/recuperar-senha", json={"email": "ausente@exemplo.com"})
        self.assertEqual(conhecido.json, desconhecido.json)
        self.assertEqual(self.firebase.emails_enviados, ["teste@exemplo.com"])

    def test_recuperacao_so_para_conta_ativa_e_sem_pedido_recente(self):
        self.banco.recuperacoes_liberadas = False  # simula o intervalo de 1 minuto
        resposta = self.cliente.post("/api/recuperar-senha", json={"email": "teste@exemplo.com"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(self.firebase.emails_enviados, [])
        self.banco.recuperacoes_liberadas = True
        self.banco.usuarios["uid-1"]["ativo"] = False
        self.cliente.post("/api/recuperar-senha", json={"email": "teste@exemplo.com"})
        self.assertEqual(self.firebase.emails_enviados, [])

    def test_recuperacao_com_falha_no_firebase_ou_no_neon(self):
        normal = self.cliente.post("/api/recuperar-senha", json={"email": "ausente@exemplo.com"})
        self.firebase.indisponivel = True
        falha_firebase = self.cliente.post("/api/recuperar-senha", json={"email": "teste@exemplo.com"})
        self.firebase.indisponivel = False
        self.banco.fora_do_ar = True
        falha_banco = self.cliente.post("/api/recuperar-senha", json={"email": "teste@exemplo.com"})
        self.assertEqual(falha_firebase.status_code, 200)
        self.assertEqual(falha_firebase.json, normal.json)
        self.assertEqual(falha_banco.json, normal.json)

    def test_recuperacao_valida_email_e_limita_pedidos(self):
        self.assertEqual(self.cliente.post("/api/recuperar-senha", json={"email": "sem-arroba"}).status_code, 400)
        self.assertEqual(self.cliente.post("/api/recuperar-senha", json={}).status_code, 400)
        for pedido in range(5):
            self.assertEqual(self.cliente.post("/api/recuperar-senha", json={"email": "teste@exemplo.com"}).status_code, 200)
        self.assertEqual(self.cliente.post("/api/recuperar-senha", json={"email": "teste@exemplo.com"}).status_code, 429)

    def test_rota_antiga_de_codigo_nao_existe_mais(self):
        self.assertEqual(self.cliente.post("/api/alterar-senha", json={}, headers=self.headers).status_code, 404)

    # ---------- restaurante (sem mudanças) ----------

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


class TesteValidacoes(unittest.TestCase):
    def test_senha_email_e_nome(self):
        self.assertTrue(senha_valida("Senha12345"))
        for senha in ["curta1", "somenteletras", "12345678", "a1" * 65, None, 12345678]:
            self.assertFalse(senha_valida(senha))
        self.assertTrue(email_valido("a@b.com"))
        for email in ["sem-arroba", "a@b", "a b@c.com", "@c.com", "a@.com", "a@c.", None]:
            self.assertFalse(email_valido(email))
        self.assertTrue(nome_valido("Ana"))
        for nome in ["", " a ", "x" * 101, None]:
            self.assertFalse(nome_valido(nome))


class TesteBancoNeon(unittest.TestCase):
    def test_sem_endereco_configurado(self):
        with patch.dict("os.environ", {"DATABASE_URL": ""}):
            with self.assertRaises(BancoErro):
                modulo_banco.buscar_usuario_por_uid("x")

    def test_falha_de_conexao_vira_banco_erro(self):
        with patch.dict("os.environ", {"DATABASE_URL": "postgresql://u:p@localhost/db"}):
            with patch("banco.psycopg.connect", side_effect=modulo_banco.psycopg.OperationalError("sem rede")):
                with self.assertRaises(BancoErro):
                    modulo_banco.buscar_usuario_por_uid("x")


def resposta_http(status, corpo):
    resposta = MagicMock()
    resposta.status_code = status
    resposta.json.return_value = corpo
    return resposta


def erro_firebase(status, mensagem):
    return resposta_http(status, {"error": {"code": status, "message": mensagem}})


@patch.dict("os.environ", {"FIREBASE_API_KEY": "chave-de-teste"})
class TesteIntegracaoFirebase(unittest.TestCase):
    def test_login_correto_devolve_uid_e_momento_do_token(self):
        with patch("autenticacao.requests.post", return_value=resposta_http(200, {"idToken": "token"})) as post, \
                patch("autenticacao._app"), \
                patch("autenticacao.auth.verify_id_token", return_value={"uid": "u1", "email": "a@b.com", "iat": 123}):
            conta = modulo_autenticacao.entrar("a@b.com", "Senha12345")
        self.assertEqual(conta, {"uid": "u1", "email": "a@b.com", "iat": 123})
        self.assertEqual(post.call_args.kwargs["params"], {"key": "chave-de-teste"})
        self.assertEqual(post.call_args.kwargs["json"]["password"], "Senha12345")

    def test_erros_do_login_sao_traduzidos(self):
        casos = {
            "INVALID_LOGIN_CREDENTIALS": "credenciais",
            "EMAIL_NOT_FOUND": "credenciais",
            "INVALID_PASSWORD": "credenciais",
            "USER_DISABLED": "desativada",
            "TOO_MANY_ATTEMPTS_TRY_LATER : Access to this account has been temporarily disabled": "muitas_tentativas",
            "API_KEY_INVALID": "configuracao",
            "OPERATION_NOT_ALLOWED : Password sign-in is disabled for this project.": "configuracao",
        }
        for mensagem, tipo in casos.items():
            with patch("autenticacao.requests.post", return_value=erro_firebase(400, mensagem)):
                with self.assertRaises(ErroAutenticacao) as contexto:
                    modulo_autenticacao.entrar("a@b.com", "x")
            self.assertEqual(contexto.exception.tipo, tipo, mensagem)

    def test_sem_internet_ou_sem_chave(self):
        with patch("autenticacao.requests.post", side_effect=modulo_autenticacao.requests.ConnectionError()):
            with self.assertRaises(ErroAutenticacao) as contexto:
                modulo_autenticacao.entrar("a@b.com", "x")
        self.assertEqual(contexto.exception.tipo, "indisponivel")
        with patch.dict("os.environ", {"FIREBASE_API_KEY": ""}):
            with self.assertRaises(ErroAutenticacao) as contexto:
                modulo_autenticacao.entrar("a@b.com", "x")
        self.assertEqual(contexto.exception.tipo, "configuracao")

    def test_token_de_outro_projeto_e_recusado_com_mensagem_clara(self):
        with patch("autenticacao.requests.post", return_value=resposta_http(200, {"idToken": "token"})), \
                patch("autenticacao._app"), \
                patch("autenticacao.auth.verify_id_token", side_effect=ValueError("audience errada")):
            with self.assertRaises(ErroAutenticacao) as contexto:
                modulo_autenticacao.entrar("a@b.com", "x")
        self.assertEqual(contexto.exception.tipo, "configuracao")

    def test_pedido_de_recuperacao(self):
        with patch("autenticacao.requests.post", return_value=resposta_http(200, {"email": "a@b.com"})) as post:
            modulo_autenticacao.enviar_recuperacao("a@b.com")
        self.assertEqual(post.call_args.kwargs["json"], {"requestType": "PASSWORD_RESET", "email": "a@b.com"})
        self.assertEqual(post.call_args.kwargs["headers"]["X-Firebase-Locale"], "pt-BR")
        self.assertTrue(post.call_args.args[0].endswith("accounts:sendOobCode"))
        with patch("autenticacao.requests.post", return_value=erro_firebase(400, "EMAIL_NOT_FOUND")):
            modulo_autenticacao.enviar_recuperacao("a@b.com")  # não deve levantar erro
        with patch("autenticacao.requests.post", return_value=erro_firebase(400, "API_KEY_INVALID")):
            with self.assertRaises(ErroAutenticacao):
                modulo_autenticacao.enviar_recuperacao("a@b.com")

    def test_conferencia_da_sessao(self):
        def conta(desativada=False, valido_apos_ms=None):
            return SimpleNamespace(disabled=desativada, tokens_valid_after_timestamp=valido_apos_ms)

        with patch("autenticacao._app"):
            with patch("autenticacao.auth.get_user", return_value=conta(valido_apos_ms=1_000_000)):
                self.assertTrue(modulo_autenticacao.conta_ainda_valida("u1", 1000))
                self.assertFalse(modulo_autenticacao.conta_ainda_valida("u1", 999))
            with patch("autenticacao.auth.get_user", return_value=conta()):
                self.assertTrue(modulo_autenticacao.conta_ainda_valida("u1", 1))
            with patch("autenticacao.auth.get_user", return_value=conta(desativada=True)):
                self.assertFalse(modulo_autenticacao.conta_ainda_valida("u1", 10**10))
            with patch("autenticacao.auth.get_user", side_effect=modulo_autenticacao.auth.UserNotFoundError("sumiu")):
                self.assertFalse(modulo_autenticacao.conta_ainda_valida("u1", 10**10))

    def test_chave_de_api_confere_com_login_falso(self):
        with patch("autenticacao.requests.post", return_value=erro_firebase(400, "INVALID_LOGIN_CREDENTIALS")):
            modulo_autenticacao.testar_chave_api()  # chave boa: não levanta erro
        with patch("autenticacao.requests.post", return_value=erro_firebase(400, "API_KEY_INVALID")):
            with self.assertRaises(ErroAutenticacao):
                modulo_autenticacao.testar_chave_api()


class TesteCadastroDeUsuario(unittest.TestCase):
    def setUp(self):
        self.banco = BancoFalso()
        self.banco.usuarios = {}
        self.firebase = AutenticacaoFalsa()
        self.firebase.contas = {"ja-existe@exemplo.com": {"uid": "uid-antigo", "senha": "Qualquer123"}}
        for nome, valor in (("banco", self.banco), ("autenticacao", self.firebase)):
            original = getattr(modulo_cadastro, nome)
            setattr(modulo_cadastro, nome, valor)
            self.addCleanup(setattr, modulo_cadastro, nome, original)
        patcher = patch("cadastrar_usuario.load_dotenv")
        patcher.start()
        self.addCleanup(patcher.stop)

    def cadastrar(self, entradas, senhas=("Senha12345", "Senha12345")):
        with patch("builtins.input", side_effect=entradas), patch("cadastrar_usuario.getpass", side_effect=list(senhas)), \
                patch("builtins.print"):
            modulo_cadastro.cadastrar_usuario()

    def test_cria_conta_no_firebase_e_registro_no_neon(self):
        self.cadastrar(["Ana Souza", "Ana@Exemplo.com"])
        self.assertEqual(self.firebase.contas["ana@exemplo.com"]["senha"], "Senha12345")
        usuario = self.banco.buscar_usuario_por_email("ana@exemplo.com")
        self.assertEqual(usuario["nome"], "Ana Souza")
        self.assertEqual(usuario["firebase_uid"], self.firebase.contas["ana@exemplo.com"]["uid"])

    def test_dados_invalidos_nao_criam_nada(self):
        self.cadastrar(["A", "ana@exemplo.com"])
        self.cadastrar(["Ana", "sem-arroba"])
        self.cadastrar(["Ana", "ana@exemplo.com"], senhas=("curta", "curta"))
        self.cadastrar(["Ana", "ana@exemplo.com"], senhas=("Senha12345", "Diferente123"))
        self.assertEqual(self.banco.usuarios, {})
        self.assertEqual(self.firebase.criadas, [])

    def test_desfaz_a_conta_do_firebase_se_o_neon_falhar(self):
        self.banco.criar_usuario = MagicMock(side_effect=BancoErro("Neon fora do ar"))
        self.cadastrar(["Ana", "ana@exemplo.com"])
        self.assertEqual(self.firebase.removidas, self.firebase.criadas)
        self.assertEqual(len(self.firebase.removidas), 1)

    def test_libera_conta_que_ja_existe_no_firebase(self):
        self.cadastrar(["Bia", "ja-existe@exemplo.com", "s"], senhas=())
        self.assertEqual(self.banco.buscar_usuario_por_email("ja-existe@exemplo.com")["firebase_uid"], "uid-antigo")
        self.assertEqual(self.firebase.contas["ja-existe@exemplo.com"]["senha"], "Qualquer123")
        self.assertEqual(self.firebase.criadas, [])

    def test_nao_cadastra_duas_vezes_o_mesmo_email(self):
        self.cadastrar(["Ana", "ana@exemplo.com"])
        self.cadastrar(["Ana", "ana@exemplo.com"])
        self.assertEqual(len(self.firebase.criadas), 1)


if __name__ == "__main__":
    unittest.main()
