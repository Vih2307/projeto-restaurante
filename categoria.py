class Categoria:
    def __init__(self, sobremesa, prato_principal, entrada, bebida):
        self.sobremesa = sobremesa
        self.prato_principal = prato_principal
        self.entrada = entrada
        self.bebida = bebida


sobremesa = [
    {"nome": "Pudim", "preco": 12.00},
    {"nome": "Sorvete", "preco": 10.00},
    {"nome": "Banana Split", "preco": 18.00}
]

prato_principal = [
    {"nome": "Arroz carreteiro", "preco": 30.00},
    {"nome": "Lasanha bolonhesa", "preco": 28.00},
    {"nome": "Parmegiana", "preco": 35.00}
]

entrada = [
    {"nome": "Salada Caesar", "preco": 19.99},
    {"nome": "Bruschetta", "preco": 28.00},
    {"nome": "Salada Americana", "preco": 35.00}
]

bebida = [
    {"nome": "Coca-cola", "preco": 8.00},
    {"nome": "Suco", "preco": 7.00},
    {"nome": "Agua", "preco": 5.00}
]

categoria = Categoria(
    sobremesa,
    prato_principal,
    entrada,
    bebida
)
