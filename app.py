import os
import secrets
import time
from flask import Flask, jsonify, render_template, request, session, redirect
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from usuario import carregar_usuarios, salvar_usuarios, buscar_usuario, senha_valida, email_valido
from email_recuperacao import enviar_codigo

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
usuarios = carregar_usuarios()
tentativas_login = {}


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


@app.before_request
def verificar_acesso():
    rotas_publicas = ["login", "entrar", "recuperar_senha", "alterar_senha", "static"]
    if request.endpoint is None or request.endpoint in rotas_publicas:
        return

    usuario = buscar_usuario(usuarios, session.get("email"))
    if usuario is None or session.get("versao") != usuario.versao:
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


@app.route("/api/login", methods=["POST"])
def entrar():
    dados = ler_dados()
    email = dados.get("email", "")
    senha = dados.get("senha", "")
    if not isinstance(email, str) or not isinstance(senha, str) or len(senha) > 128:
        return jsonify({"erro": "Informe e-mail e senha válidos."}), 400

    ip = request.remote_addr
    agora = time.time()
    tentativa = tentativas_login.get(ip)
    if tentativa is None or agora > tentativa["validade"]:
        tentativa = {"quantidade": 0, "validade": agora + 300}
        tentativas_login[ip] = tentativa
    if tentativa["quantidade"] >= 10:
        return jsonify({"erro": "Aguarde 5 minutos antes de tentar novamente."}), 429
    tentativa["quantidade"] += 1

    usuario = buscar_usuario(usuarios, email.strip().lower())
    if usuario is None or not usuario.verificar_senha(senha):
        return jsonify({"erro": "E-mail ou senha incorretos."}), 401

    session.clear()
    session["email"] = usuario.email
    session["versao"] = usuario.versao
    session["token"] = secrets.token_hex(16)
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

    mensagem = "Se o e-mail estiver cadastrado, o código será enviado."
    usuario = buscar_usuario(usuarios, email.strip().lower())
    if usuario is None:
        return jsonify({"mensagem": mensagem})

    agora = time.time()
    if agora - usuario.ultimo_envio < 60:
        return jsonify({"mensagem": mensagem})

    usuario.ultimo_envio = agora
    usuario.codigo = ""
    usuario.validade_codigo = 0
    salvar_usuarios(usuarios)
    codigo = str(secrets.randbelow(1000000)).zfill(6)
    try:
        enviar_codigo(usuario.email, codigo)
    except (OSError, ValueError):
        app.logger.error("Não foi possível enviar o e-mail. Verifique o arquivo .env.")
        return jsonify({"mensagem": mensagem})

    usuario.codigo = generate_password_hash(codigo)
    usuario.validade_codigo = agora + 600
    usuario.tentativas = 0
    salvar_usuarios(usuarios)
    return jsonify({"mensagem": mensagem})


@app.route("/api/alterar-senha", methods=["POST"])
def alterar_senha():
    dados = ler_dados()
    email = dados.get("email", "")
    codigo = dados.get("codigo", "")
    senha = dados.get("senha", "")
    confirmacao = dados.get("confirmacao", "")
    if not email_valido(email) or not isinstance(codigo, str) or len(codigo) != 6 or not codigo.isdigit():
        return jsonify({"erro": "Informe e-mail e código de 6 números."}), 400
    if not senha_valida(senha):
        return jsonify({"erro": "Use de 8 a 128 caracteres, com letras e números."}), 400
    if senha != confirmacao:
        return jsonify({"erro": "As senhas não são iguais."}), 400

    usuario = buscar_usuario(usuarios, email.strip().lower())
    if usuario is None or not usuario.codigo or time.time() > usuario.validade_codigo or usuario.tentativas >= 5:
        return jsonify({"erro": "Código inválido ou expirado. Solicite outro."}), 400

    usuario.tentativas += 1
    if not check_password_hash(usuario.codigo, codigo):
        salvar_usuarios(usuarios)
        return jsonify({"erro": "Código inválido ou expirado. Solicite outro."}), 400

    usuario.alterar_senha(senha)
    salvar_usuarios(usuarios)
    session.clear()
    return jsonify({"mensagem": "Senha alterada. Entre com sua nova senha."})

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
