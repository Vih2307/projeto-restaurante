from flask import Flask, jsonify, render_template, request

from caixa import Caixa
from categoria import categoria
from estoque import Estoque
from mesa import Mesa
from pedido import Pedido


app = Flask(__name__)

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
    return render_template("index.html")


@app.route("/api/dados")
def obter_dados():
    pedidos_abertos = [
        pedido_para_json(pedido)
        for pedido in pedidos
        if pedido.status != "Finalizado"
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

    dados = request.get_json(silent=True) or {}
    numero_mesa = dados.get("mesa")
    itens = dados.get("itens", [])

    try:
        numero_mesa = int(numero_mesa)
    except (TypeError, ValueError):
        return jsonify({"erro": "Informe uma mesa válida."}), 400

    mesa_escolhida = next(
        (mesa for mesa in mesas if mesa.numero == numero_mesa),
        None
    )

    if mesa_escolhida is None:
        return jsonify({"erro": "Mesa não encontrada."}), 404

    if not itens:
        return jsonify({"erro": "Adicione pelo menos um item ao pedido."}), 400

    itens_validados = []
    for item in itens:
        produto = buscar_produto(item.get("nome"))

        try:
            quantidade = int(item.get("quantidade", 0))
        except (TypeError, ValueError):
            quantidade = 0

        if produto is None or quantidade <= 0:
            return jsonify({"erro": "Existe um item inválido no pedido."}), 400

        disponivel, mensagem = estoque.verificar_disponibilidade(
            produto,
            quantidade
        )

        if not disponivel:
            return jsonify({"erro": mensagem}), 400

        itens_validados.append((produto, quantidade))

    pedido = next(
        (
            pedido
            for pedido in pedidos
            if pedido.mesa.numero == numero_mesa
            and pedido.status != "Finalizado"
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
    dados = request.get_json(silent=True) or {}
    forma_pagamento = dados.get("forma_pagamento")

    formas_validas = ["Dinheiro", "PIX", "Débito", "Crédito"]

    if pedido is None or pedido.status == "Finalizado":
        return jsonify({"erro": "Pedido aberto não encontrado."}), 404

    if forma_pagamento not in formas_validas:
        return jsonify({"erro": "Escolha uma forma de pagamento válida."}), 400

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
    dados = request.get_json(silent=True) or {}
    nome = dados.get("nome")

    try:
        quantidade = int(dados.get("quantidade", 0))
    except (TypeError, ValueError):
        quantidade = 0

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


iniciar_sistema()


if __name__ == "__main__":
    app.run(debug=True)
