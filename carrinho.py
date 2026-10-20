class Carrinho:
    def __init__(self):
        self.itens = []
        self.forma_pagamento = None
        self.status = "Aberto"

    def adicionar_item(self, nome, preco, quantidade):
        if not isinstance(nome, str) or not nome.strip():
            raise ValueError("Informe o nome do produto.")
        if type(quantidade) is not int or quantidade <= 0:
            raise ValueError("A quantidade deve ser um número inteiro positivo.")
        if type(preco) not in [int, float] or not 0 < preco <= 100000:
            raise ValueError("Informe um preço válido.")
        if self.status in ["Finalizado", "Cancelado"]:
            raise ValueError("Este pedido já foi encerrado.")
        for produto in self.itens:
            if produto["nome"] == nome:
                produto["quantidade"] += quantidade
                return
        self.itens.append({"nome": nome, "preco": preco, "quantidade": quantidade})

    def calcular_total(self):
        total = 0
        for item in self.itens:
            total += item["preco"] * item["quantidade"]
        return round(total, 2)

    def escolher_pagamento(self, forma):
        formas = ["Dinheiro", "PIX", "Débito", "Crédito"]
        if forma not in formas:
            raise ValueError("Forma de pagamento inválida.")
        self.forma_pagamento = forma

    def finalizar_compra(self):
        if self.status in ["Finalizado", "Cancelado"]:
            raise ValueError("A compra já foi encerrada.")
        if not self.itens or self.forma_pagamento is None:
            raise ValueError("Adicione itens e escolha o pagamento.")
        self.status = "Finalizado"
        return self.calcular_total()
