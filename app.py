import os
import secrets
import time
from flask import Flask, jsonify, render_template, request, session, redirect
from dotenv import load_dotenv
import autenticacao
import banco
from autenticacao import ErroAutenticacao
from banco import BancoErro
from usuario import email_valido

from caixa import Caixa
from categoria import categoria
from estoque import Estoque
from mesa import Mesa
from pedido import Pedido


load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("CHAVE_SECRETA") or secrets.token_hex(32)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["MAX_CONTENT_LENGTH"] = 65536
tentativas_login = {}
tentativas_recuperacao = {}

# De quanto em quanto tempo a sessão é conferida de novo no Firebase e no Neon.
INTERVALO_CONFERENCIA = 300  # 5 minutos
# Se o Firebase ou o Neon ficarem fora do ar, a sessão continua valendo por este tempo.
TOLERANCIA_FALHA = 1800  # 30 minutos


def ler_dados():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return {}
    return dados


def ler_quantidade(valor):
    if isinstance(valor, bool) or not isinstance(valor, (str, int)):
        return 0
    try:
        quantidade = int(valor)
    except ValueError:
        return 0
    if quantidade < 1 or quantidade > 10000:
        return 0
    return quantidade


def passou_do_limite(tabela, chave, maximo, janela):
    """Conta uma tentativa. Devolve True quando o limite da janela (em segundos) já foi atingido."""
    agora = time.time()
    registro = tabela.get(chave)
    if registro is None or agora > registro["validade"]:
        registro = {"quantidade": 0, "validade": agora + janela}
        tabela[chave] = registro
    if registro["quantidade"] >= maximo:
        return True
    registro["quantidade"] += 1
    return False


def sessao_valida():
    """Confere se a sessão pertence a um funcionário que ainda pode usar o sistema.

    A cada INTERVALO_CONFERENCIA a sessão é conferida de novo: a conta precisa continuar
    ativa no Neon e não pode ter sido desativada, apagada ou ter a senha redefinida no
    Firebase depois do login. Se o Firebase ou o Neon estiverem fora do ar, a sessão
    continua valendo por até TOLERANCIA_FALHA, para não parar o restaurante.
    """
    uid = session.get("uid")
    if not uid:
        return False

    agora = time.time()
    if agora - session.get("tentou_em", 0) >= INTERVALO_CONFERENCIA:
        session["tentou_em"] = agora
        try:
            usuario = banco.buscar_usuario_por_uid(uid)
            if usuario is None or not usuario["ativo"]:
                return False
            if not autenticacao.conta_ainda_valida(uid, session.get("iat", 0)):
                return False
            session["verificado_em"] = agora
        except (BancoErro, ErroAutenticacao) as erro:
            app.logger.warning("Não foi possível conferir a sessão agora: %s", erro)

    return agora - session.get("verificado_em", 0) < TOLERANCIA_FALHA


@app.before_request
def verificar_acesso():
    rotas_publicas = ["login", "entrar", "recuperar_senha", "static"]
    if request.endpoint is None or request.endpoint in rotas_publicas:
        return

    if not sessao_valida():
        session.clear()
        if request.path == "/":
            return redirect("/login")
        return jsonify({"erro": "Faça login para continuar."}), 401

    if request.method == "POST":
        token = request.headers.get("X-CSRF-Token")
        if not token or token != session.get("token"):
            return jsonify({"erro": "Atualize a página e tente novamente."}), 403


@app.route("/login")
def login():
    return render_template("login.html")


def erro_de_login(erro):
    """Converte uma falha do Firebase em resposta para a tela de login."""
    if erro.tipo == "credenciais":
        return jsonify({"erro": "E-mail ou senha incorretos."}), 401
    if erro.tipo == "desativada":
        return jsonify({"erro": "Sua conta está desativada. Fale com o gerente."}), 403
    if erro.tipo == "muitas_tentativas":
        return jsonify({"erro": "Muitas tentativas. Aguarde alguns minutos ou use \"Esqueci minha senha\"."}), 429
    app.logger.error("Falha no login pelo Firebase: %s", erro.mensagem)
    if erro.tipo == "configuracao":
        return jsonify({"erro": "O login não está configurado corretamente. Avise o responsável pelo sistema."}), 503
    return jsonify({"erro": "Não foi possível falar com o serviço de login. Tente novamente."}), 503


@app.route("/api/login", methods=["POST"])
def entrar():
    dados = ler_dados()
    email = dados.get("email", "")
    senha = dados.get("senha", "")
    if not isinstance(email, str) or not isinstance(senha, str) or len(senha) > 128:
        return jsonify({"erro": "Informe e-mail e senha válidos."}), 400

    if passou_do_limite(tentativas_login, request.remote_addr, 10, 300):
        return jsonify({"erro": "Aguarde 5 minutos antes de tentar novamente."}), 429

    email = email.strip().lower()
    if not email_valido(email) or not senha:
        return jsonify({"erro": "E-mail ou senha incorretos."}), 401

    try:
        conta = autenticacao.entrar(email, senha)
        usuario = banco.buscar_usuario_por_uid(conta["uid"])
    except ErroAutenticacao as erro:
        return erro_de_login(erro)
    except BancoErro as erro:
        app.logger.error("Falha ao consultar o banco no login: %s", erro)
        return jsonify({"erro": "Não foi possível consultar o banco de dados. Tente novamente."}), 503

    if usuario is None or not usuario["ativo"]:
        return jsonify({"erro": "Seu acesso não está liberado. Fale com o gerente."}), 403

    agora = time.time()
    session.clear()
    session["uid"] = conta["uid"]
    session["email"] = usuario["email"]
    session["nome"] = usuario["nome"]
    session["iat"] = conta["iat"]
    session["token"] = secrets.token_hex(16)
    session["verificado_em"] = agora
    session["tentou_em"] = agora
    try:
        banco.registrar_login(conta["uid"])
    except BancoErro as erro:
        app.logger.warning("Não foi possível registrar o horário do login: %s", erro)
    return jsonify({"mensagem": "Login realizado."})


@app.route("/api/sair", methods=["POST"])
def sair():
    session.clear()
    return jsonify({"mensagem": "Você saiu do sistema."})


@app.route("/api/recuperar-senha", methods=["POST"])
def recuperar_senha():
    dados = ler_dados()
    email = dados.get("email", "")
    if not email_valido(email):
        return jsonify({"erro": "Informe um e-mail válido."}), 400

    if passou_do_limite(tentativas_recuperacao, request.remote_addr, 5, 600):
        return jsonify({"erro": "Muitos pedidos seguidos. Aguarde alguns minutos."}), 429

    # A resposta é sempre a mesma, para não revelar quais e-mails estão cadastrados.
    mensagem = "Se o e-mail estiver cadastrado, enviaremos um link para redefinir a senha."
    email = email.strip().lower()
    try:
        # Só funcionário ativo no Neon recebe o e-mail, no máximo um por minuto.
        if banco.reservar_envio_recuperacao(email, 60):
            autenticacao.enviar_recuperacao(email)
    except (BancoErro, ErroAutenticacao) as erro:
        app.logger.error("Não foi possível enviar o e-mail de recuperação: %s", erro)
    return jsonify({"mensagem": mensagem})


mesas = [Mesa("Livre", numero, False) for numero in range(1, 9)]
pedidos = []
caixa = Caixa()
estoque = Estoque()
numero_pedido = 1

cardapio = (
    categoria.entrada
    + categoria.prato_principal
    + categoria.bebida
    + categoria.sobremesa
)


def iniciar_sistema():
    caixa.abrir_caixa()

    for produto in cardapio:
        estoque.cadastrar_produto_pronto(
            produto["nome"],
            quantidade_inicial=15,
            unidade="un",
            estoque_minimo=5
        )


def buscar_pedido(numero):
    for pedido in pedidos:
        if pedido.numero == numero:
            return pedido
    return None


def buscar_produto(nome):
    for produto in cardapio:
        if produto["nome"] == nome:
            return produto
    return None


def pedido_para_json(pedido):
    return {
        "numero": pedido.numero,
        "mesa": pedido.mesa.numero,
        "itens": pedido.itens,
        "total": pedido.calcular_total(),
        "status": pedido.status,
        "forma_pagamento": pedido.forma_pagamento
    }


@app.route("/")
def pagina_inicial():
    return render_template("index.html", token=session["token"])


@app.route("/api/dados")
def obter_dados():
    pedidos_abertos = [
        pedido_para_json(pedido)
        for pedido in pedidos
        if pedido.status not in ["Finalizado", "Cancelado"]
    ]

    vendas = [pedido_para_json(pedido) for pedido in caixa.vendas]

    itens_estoque = []
    for item in estoque.produtos_prontos.values():
        itens_estoque.append({
            "nome": item["nome"],
            "quantidade": item["quantidade"],
            "unidade": item["unidade"],
            "estoque_minimo": item["estoque_minimo"],
            "baixo": item["quantidade"] <= item["estoque_minimo"]
        })

    quantidade_vendas = len(caixa.vendas)
    ticket_medio = 0
    if quantidade_vendas > 0:
        ticket_medio = caixa.total_vendido / quantidade_vendas

    return jsonify({
        "mesas": [
            {"numero": mesa.numero, "status": mesa.status}
            for mesa in mesas
        ],
        "cardapio": cardapio,
        "pedidos": pedidos_abertos,
        "vendas": vendas,
        "caixa": {
            "status": caixa.status,
            "total_vendido": caixa.total_vendido,
            "quantidade_vendas": quantidade_vendas,
            "ticket_medio": ticket_medio
        },
        "estoque": itens_estoque
    })


@app.route("/api/pedidos", methods=["POST"])
def criar_pedido():
    global numero_pedido

    dados = ler_dados()
    numero_mesa = dados.get("mesa")
    itens = dados.get("itens", [])

    numero_mesa = ler_quantidade(numero_mesa)
    if numero_mesa == 0:
        return jsonify({"erro": "Informe uma mesa válida."}), 400

    mesa_escolhida = next(
        (mesa for mesa in mesas if mesa.numero == numero_mesa),
        None
    )

    if mesa_escolhida is None:
        return jsonify({"erro": "Mesa não encontrada."}), 404

    if not isinstance(itens, list) or not itens or len(itens) > 100:
        return jsonify({"erro": "Adicione pelo menos um item ao pedido."}), 400

    itens_agrupados = {}
    for item in itens:
        if not isinstance(item, dict):
            return jsonify({"erro": "Existe um item inválido no pedido."}), 400
        nome = item.get("nome")
        quantidade = ler_quantidade(item.get("quantidade"))
        if not isinstance(nome, str) or quantidade == 0:
            return jsonify({"erro": "Informe produto e quantidade inteira válida."}), 400
        if nome not in itens_agrupados:
            itens_agrupados[nome] = 0
        itens_agrupados[nome] += quantidade

    itens_validados = []
    for nome in itens_agrupados:
        produto = buscar_produto(nome)
        quantidade = itens_agrupados[nome]
        if produto is None:
            return jsonify({"erro": "Produto não encontrado."}), 400
        disponivel, mensagem = estoque.verificar_disponibilidade(produto, quantidade)
        if not disponivel:
            return jsonify({"erro": mensagem}), 400
        itens_validados.append((produto, quantidade))

    pedido = next(
        (
            pedido
            for pedido in pedidos
            if pedido.mesa.numero == numero_mesa
            and pedido.status not in ["Finalizado", "Cancelado"]
        ),
        None
    )

    if pedido is None:
        if mesa_escolhida.status != "Livre":
            return jsonify({"erro": "Essa mesa não está disponível."}), 400

        mesa_escolhida.ocupar()
        pedido = Pedido(numero_pedido, mesa_escolhida)
        pedidos.append(pedido)
        numero_pedido += 1

    for produto, quantidade in itens_validados:
        estoque.baixar_produto(produto, quantidade, pedido.numero)
        pedido.adicionar_item(
            produto["nome"],
            produto["preco"],
            quantidade
        )

    pedido.atualizar_status("Em preparo")

    return jsonify({
        "mensagem": f"Pedido {pedido.numero} enviado com sucesso.",
        "pedido": pedido_para_json(pedido)
    }), 201


@app.route("/api/pedidos/<int:numero>/finalizar", methods=["POST"])
def finalizar_pedido(numero):
    pedido = buscar_pedido(numero)
    dados = ler_dados()
    forma_pagamento = dados.get("forma_pagamento")

    formas_validas = ["Dinheiro", "PIX", "Débito", "Crédito"]

    if pedido is None or pedido.status in ["Finalizado", "Cancelado"]:
        return jsonify({"erro": "Pedido aberto não encontrado."}), 404

    if forma_pagamento not in formas_validas:
        return jsonify({"erro": "Escolha uma forma de pagamento válida."}), 400

    if caixa.status != "Aberto":
        return jsonify({"erro": "O caixa está fechado."}), 400

    pedido.mesa.pedir_conta()
    pedido.escolher_pagamento(forma_pagamento)
    caixa.registrar_venda(pedido)
    pedido.mesa.liberar()

    return jsonify({
        "mensagem": f"Conta da mesa {pedido.mesa.numero} finalizada.",
        "pedido": pedido_para_json(pedido)
    })


@app.route("/api/estoque/entrada", methods=["POST"])
def repor_estoque():
    dados = ler_dados()
    nome = dados.get("nome")
    if not isinstance(nome, str):
        return jsonify({"erro": "Informe um produto válido."}), 400

    quantidade = ler_quantidade(dados.get("quantidade"))

    if quantidade <= 0:
        return jsonify({"erro": "A quantidade deve ser maior que zero."}), 400

    sucesso = estoque.entrada(
        nome,
        quantidade,
        tipo="produto_pronto",
        motivo="Reposição do gerente"
    )

    if not sucesso:
        return jsonify({"erro": "Produto não encontrado no estoque."}), 404

    return jsonify({"mensagem": f"Foram adicionadas {quantidade} unidades de {nome}."})


@app.route("/api/pedidos/<int:numero>/status", methods=["POST"])
def mudar_status(numero):
    pedido = buscar_pedido(numero)
    if pedido is None:
        return jsonify({"erro": "Pedido não encontrado."}), 404
    dados = ler_dados()
    novo_status = dados.get("status")
    if pedido.status == "Em preparo" and novo_status == "Pronto":
        pedido.atualizar_status("Pronto")
    elif pedido.status == "Pronto" and novo_status == "Entregue":
        pedido.atualizar_status("Entregue")
    else:
        return jsonify({"erro": "Mudança de status inválida."}), 400
    return jsonify({"mensagem": "Status atualizado.", "pedido": pedido_para_json(pedido)})


@app.route("/api/pedidos/<int:numero>/cancelar", methods=["POST"])
def cancelar_pedido(numero):
    pedido = buscar_pedido(numero)
    if pedido is None:
        return jsonify({"erro": "Pedido não encontrado."}), 404
    if pedido.status != "Em preparo":
        return jsonify({"erro": "Só é possível cancelar um pedido em preparo."}), 400
    dados = ler_dados()
    motivo = dados.get("motivo", "")
    if not isinstance(motivo, str) or len(motivo.strip()) < 5 or len(motivo.strip()) > 200:
        return jsonify({"erro": "Informe um motivo entre 5 e 200 caracteres."}), 400
    for item in pedido.itens:
        estoque.entrada(item["nome"], item["quantidade"], "produto_pronto", "Cancelamento: " + motivo.strip())
    pedido.atualizar_status("Cancelado")
    pedido.mesa.liberar()
    return jsonify({"mensagem": "Pedido cancelado. Estoque devolvido."})


iniciar_sistema()


if __name__ == "__main__":
    app.run(debug=False, threaded=False)
