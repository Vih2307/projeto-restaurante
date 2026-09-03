from datetime import datetime


class Estoque:

    def __init__(self):
        self.ingredientes = {}
        self.produtos_prontos = {}
        self.movimentacoes = []

    # =========================
    # CADASTRO
    # =========================

    def cadastrar_ingrediente(
        self,
        nome,
        quantidade_inicial,
        unidade,
        estoque_minimo
    ):
        self.ingredientes[nome] = {
            "nome": nome,
            "quantidade": float(quantidade_inicial),
            "unidade": unidade,
            "estoque_minimo": float(estoque_minimo)
        }

    def cadastrar_produto_pronto(
        self,
        nome,
        quantidade_inicial,
        unidade="un",
        estoque_minimo=0
    ):
        self.produtos_prontos[nome] = {
            "nome": nome,
            "quantidade": float(quantidade_inicial),
            "unidade": unidade,
            "estoque_minimo": float(estoque_minimo)
        }

    # =========================
    # ENTRADA
    # =========================

    def entrada(
        self,
        nome,
        quantidade,
        tipo="ingrediente",
        motivo="Compra/Reposicao"
    ):

        quantidade = float(quantidade)

        if quantidade <= 0:
            print("A quantidade deve ser maior que zero.")
            return False

        estoque = self._obter_estoque(nome, tipo)

        if estoque is None:
            print(f"{nome} não está cadastrado no estoque.")
            return False

        estoque["quantidade"] += quantidade

        self._registrar_movimentacao(
            "Entrada",
            nome,
            quantidade,
            estoque["unidade"],
            motivo
        )

        print(
            f"Entrada registrada: +"
            f"{self._formatar(quantidade)} "
            f"{estoque['unidade']} de {nome}."
        )

        return True

    # =========================
    # SAÍDA
    # =========================

    def saida(
        self,
        nome,
        quantidade,
        tipo="ingrediente",
        motivo="Saida manual"
    ):

        quantidade = float(quantidade)

        if quantidade <= 0:
            print("A quantidade deve ser maior que zero.")
            return False

        estoque = self._obter_estoque(nome, tipo)

        if estoque is None:
            print(f"{nome} não está cadastrado no estoque.")
            return False

        if estoque["quantidade"] < quantidade:
            print(
                f"Estoque insuficiente para {nome}."
            )

            print(
                f"Disponível: "
                f"{self._formatar(estoque['quantidade'])} "
                f"{estoque['unidade']}"
            )

            print(
                f"Solicitado: "
                f"{self._formatar(quantidade)} "
                f"{estoque['unidade']}"
            )

            return False

        estoque["quantidade"] -= quantidade

        self._registrar_movimentacao(
            "Saída",
            nome,
            quantidade,
            estoque["unidade"],
            motivo
        )

        print(
            f"Saída registrada: -"
            f"{self._formatar(quantidade)} "
            f"{estoque['unidade']} de {nome}."
        )

        return True

    # =========================
    # VERIFICAR ESTOQUE
    # =========================

    def verificar_disponibilidade(
        self,
        produto,
        quantidade
    ):

        quantidade = float(quantidade)

        if produto["tipo"] == "produto_pronto":

            nome = produto["nome"]

            if nome not in self.produtos_prontos:
                return (
                    False,
                    f"{nome} não está cadastrado no estoque."
                )

            estoque = self.produtos_prontos[nome]

            if estoque["quantidade"] < quantidade:
                return (
                    False,
                    f"Estoque insuficiente de {nome}. "
                    f"Disponível: "
                    f"{self._formatar(estoque['quantidade'])} "
                    f"{estoque['unidade']}."
                )

            return True, "OK"

        for ingrediente, consumo in produto.get(
            "receita", {}
        ).items():

            necessario = float(consumo) * quantidade

            if ingrediente not in self.ingredientes:
                return (
                    False,
                    f"Ingrediente '{ingrediente}' "
                    f"não está cadastrado no estoque."
                )

            estoque = self.ingredientes[ingrediente]

            if estoque["quantidade"] < necessario:
                return (
                    False,
                    f"Estoque insuficiente de {ingrediente}. "
                    f"Disponível: "
                    f"{self._formatar(estoque['quantidade'])} "
                    f"{estoque['unidade']} | "
                    f"Necessário: "
                    f"{self._formatar(necessario)} "
                    f"{estoque['unidade']}."
                )

        return True, "OK"

    # =========================
    # BAIXAR PRODUTO
    # =========================

    def baixar_produto(
        self,
        produto,
        quantidade,
        numero_pedido=None
    ):

        disponivel, mensagem = (
            self.verificar_disponibilidade(
                produto,
                quantidade
            )
        )

        if not disponivel:
            print(
                f"Não foi possível baixar estoque: "
                f"{mensagem}"
            )

            return False

        quantidade = float(quantidade)

        nome = produto["nome"]

        if produto["tipo"] == "produto_pronto":

            estoque = self.produtos_prontos[nome]

            estoque["quantidade"] -= quantidade

            motivo = (
                f"Venda - Pedido {numero_pedido}"
                if numero_pedido is not None
                else "Venda"
            )

            self._registrar_movimentacao(
                "Saída",
                nome,
                quantidade,
                estoque["unidade"],
                motivo
            )

        else:

            motivo = (
                f"Venda - Pedido {numero_pedido} - {nome}"
                if numero_pedido is not None
                else f"Venda - {nome}"
            )

            for ingrediente, consumo in produto.get(
                "receita",
                {}
            ).items():

                quantidade_saida = (
                    float(consumo) * quantidade
                )

                estoque = self.ingredientes[
                    ingrediente
                ]

                estoque["quantidade"] -= (
                    quantidade_saida
                )

                self._registrar_movimentacao(
                    "Saída",
                    ingrediente,
                    quantidade_saida,
                    estoque["unidade"],
                    motivo
                )

        return True

    # =========================
    # BAIXAR PEDIDO
    # =========================

    def baixar_pedido(
        self,
        pedido,
        cardapio
    ):

        produtos = {
            produto["nome"]: produto
            for produto in cardapio
        }

        for item in pedido.itens:

            produto = produtos.get(
                item["nome"]
            )

            if produto is None:
                return (
                    False,
                    f"O produto '{item['nome']}' "
                    f"não foi encontrado no cardápio."
                )

            disponivel, mensagem = (
                self.verificar_disponibilidade(
                    produto,
                    item["quantidade"]
                )
            )

            if not disponivel:
                return False, mensagem

        for item in pedido.itens:

            produto = produtos[
                item["nome"]
            ]

            self.baixar_produto(
                produto,
                item["quantidade"],
                pedido.numero
            )

        pedido.estoque_baixado = True

        return (
            True,
            "Estoque atualizado com sucesso."
        )

    # =========================
    # MOSTRAR ESTOQUE
    # =========================

    def mostrar_estoque(self):

        print("\n==============================")
        print("       ESTOQUE ATUAL")
        print("==============================")

        print("\n--- INGREDIENTES ---")

        if not self.ingredientes:

            print(
                "Nenhum ingrediente cadastrado."
            )

        else:

            for item in self.ingredientes.values():

                alerta = ""

                if (
                    item["quantidade"]
                    <= item["estoque_minimo"]
                ):
                    alerta = "  ESTOQUE BAIXO"

                print(
                    f"{item['nome']}: "
                    f"{self._formatar(item['quantidade'])} "
                    f"{item['unidade']} "
                    f"(mínimo: "
                    f"{self._formatar(item['estoque_minimo'])})"
                    f"{alerta}"
                )

        print("\n--- PRODUTOS PRONTOS ---")

        if not self.produtos_prontos:

            print(
                "Nenhum produto pronto cadastrado."
            )

        else:

            for item in self.produtos_prontos.values():

                alerta = ""

                if (
                    item["quantidade"]
                    <= item["estoque_minimo"]
                ):
                    alerta = " ⚠️ ESTOQUE BAIXO"

                print(
                    f"{item['nome']}: "
                    f"{self._formatar(item['quantidade'])} "
                    f"{item['unidade']} "
                    f"(mínimo: "
                    f"{self._formatar(item['estoque_minimo'])})"
                    f"{alerta}"
                )

    # =========================
    # ESTOQUE BAIXO
    # =========================

    def mostrar_estoque_baixo(self):

        print("\n==============================")
        print("       ESTOQUE BAIXO")
        print("==============================")

        encontrados = False

        for item in self.ingredientes.values():

            if (
                item["quantidade"]
                <= item["estoque_minimo"]
            ):

                encontrados = True

                print(
                    f"Ingrediente: {item['nome']} | "
                    f"Atual: "
                    f"{self._formatar(item['quantidade'])} "
                    f"{item['unidade']} | "
                    f"Mínimo: "
                    f"{self._formatar(item['estoque_minimo'])}"
                )

        for item in self.produtos_prontos.values():

            if (
                item["quantidade"]
                <= item["estoque_minimo"]
            ):

                encontrados = True

                print(
                    f"Produto: {item['nome']} | "
                    f"Atual: "
                    f"{self._formatar(item['quantidade'])} "
                    f"{item['unidade']} | "
                    f"Mínimo: "
                    f"{self._formatar(item['estoque_minimo'])}"
                )

        if not encontrados:

            print(
                "Nenhum item está abaixo "
                "do estoque mínimo."
            )

    # =========================
    # HISTÓRICO
    # =========================

    def mostrar_historico(self):

        print("\n==============================")
        print("     HISTÓRICO DO ESTOQUE")
        print("==============================")

        if not self.movimentacoes:

            print(
                "Nenhuma movimentação registrada."
            )

            return

        for movimento in self.movimentacoes:

            print(
                f"{movimento['data']} | "
                f"{movimento['tipo']} | "
                f"{movimento['nome']} | "
                f"{self._formatar(movimento['quantidade'])} "
                f"{movimento['unidade']} | "
                f"{movimento['motivo']}"
            )

    # =========================
    # MÉTODOS INTERNOS
    # =========================

    def _obter_estoque(
        self,
        nome,
        tipo
    ):

        if tipo == "produto_pronto":
            return self.produtos_prontos.get(nome)

        return self.ingredientes.get(nome)

    def _registrar_movimentacao(
        self,
        tipo,
        nome,
        quantidade,
        unidade,
        motivo
    ):

        self.movimentacoes.append({

            "data": datetime.now().strftime(
                "%d/%m/%Y %H:%M:%S"
            ),

            "tipo": tipo,
            "nome": nome,
            "quantidade": quantidade,
            "unidade": unidade,
            "motivo": motivo
        })

    @staticmethod
    def _formatar(valor):

        valor = float(valor)

        if valor.is_integer():
            return str(int(valor))

        return (
            f"{valor:.3f}"
            .rstrip("0")
            .rstrip(".")
        )