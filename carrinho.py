class Carrinho:
    def __init__(self):
        self.itens = []
        self.forma_pagamento = None

    def adicionar_item(self, nome, preco, quantidade):
        ...

    def calcular_total(self):
        ...

    def escolher_pagamento(self, forma):
        self.forma_pagamento = forma

    def finalizar_compra(self):
        ...

    