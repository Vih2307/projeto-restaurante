from carrinho import Carrinho


class Pedido(Carrinho):
    def __init__(self, numero, mesa):
        super().__init__()
        self.numero = numero
        self.mesa = mesa
        self.status = "Aguardando"

    def remover_item(self, indice):
        if 0 <= indice < len(self.itens):
            self.itens.pop(indice)

    def alterar_quantidade(self, indice, quantidade):
        if 0 <= indice < len(self.itens):
            if quantidade > 0:
                self.itens[indice]["quantidade"] = quantidade
            else:
                self.remover_item(indice)

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
