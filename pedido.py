class Pedido:
    def __init__(self, numero, mesa):
        self.numero = numero
        self.mesa = mesa
        self.itens = []
        self.forma_pagamento = None
        self.total = 0
        self.status = "Aguardando"

    def adicionar_item(self, item, preco, quantidade):
        # Se o produto já estiver no carrinho, apenas aumenta a quantidade.
        for produto in self.itens:
            if produto["nome"] == item:
                produto["quantidade"] += quantidade
                return

        self.itens.append({
            "nome": item,
            "preco": preco,
            "quantidade": quantidade
        })

    def remover_item(self, indice):
        if 0 <= indice < len(self.itens):
            self.itens.pop(indice)

    def alterar_quantidade(self, indice, quantidade):
        if 0 <= indice < len(self.itens):
            if quantidade > 0:
                self.itens[indice]["quantidade"] = quantidade
            else:
                self.remover_item(indice)

    def calcular_total(self):
        self.total = sum(
            item["preco"] * item["quantidade"]
            for item in self.itens
        )
        return self.total

    def escolher_pagamento(self, forma):
        self.forma_pagamento = forma

    def atualizar_status(self, status):
        self.status = status

    def mostrar_pedido(self):
        print("----- PEDIDO -----")
        print(f"Pedido: {self.numero}")
        print(f"Mesa: {self.mesa.numero}")

        for item in self.itens:
            subtotal = item["preco"] * item["quantidade"]
            print(
                f"{item['quantidade']}x "
                f"{item['nome']} - "
                f"R$ {subtotal:.2f}"
            )

        print(f"Total: R$ {self.calcular_total():.2f}")
        print(f"Pagamento: {self.forma_pagamento}")
        print(f"Status: {self.status}")
