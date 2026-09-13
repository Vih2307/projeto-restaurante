class Mesa:
    def __init__(self, status, numero, reservada):
        self.status = status
        self.numero = numero
        self.reservada = reservada

    def ocupar(self):
        if self.status == "Livre":
            self.status = "Ocupada"
            print(f"Mesa {self.numero} ocupada.")
        else:
            print("Essa mesa não está disponível.")

    def liberar(self):
        self.status = "Livre"
        self.reservada = False
        print(f"Mesa {self.numero} liberada.")

    def reservar(self):
        if self.status == "Livre":
            self.reservada = True
            print(f"Mesa {self.numero} reservada.")
        else:
            print("Não é possível reservar essa mesa.")

    def pedir_conta(self):
        if self.status == "Ocupada":
            self.status = "Aguardando fechamento"
            print("Conta solicitada.")
