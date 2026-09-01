class Caixa:
    def __init__(self):
        self.status = "Fechado"
        self.total_vendido = 0
        self.vendas = []

    def abrir_caixa(self):
        self.status = "Aberto"
        print("Caixa aberto.")

    def registrar_venda(self, pedido):
        if self.status == "Fechado":
            print("O caixa está fechado.")
            return

        valor = pedido.calcular_total()
        self.vendas.append(pedido)
        self.total_vendido += valor
        pedido.status = "Finalizado"
        print(f"Venda registrada: R$ {valor:.2f}")

    def fechar_caixa(self):
        self.status = "Fechado"
        print("Caixa fechado.")

    def gerar_saldo_diario(self):
        print("----- CAIXA -----")
        print(f"Quantidade de vendas: {len(self.vendas)}")
        print(f"Total vendido: R$ {self.total_vendido:.2f}")
