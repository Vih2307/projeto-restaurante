class Categoria:
    def __init__(self, sobremesa, prato_principal, entrada, bebida):
        self.sobremesa = sobremesa
        self.prato_principal = prato_principal
        self.entrada = entrada
        self.bebida = bebida


sobremesa = [
    {"nome": "Pudim", "preco": 12.00, "categoria": "Sobremesas", "tipo": "produto_pronto"},
    {"nome": "Sorvete", "preco": 10.00, "categoria": "Sobremesas", "tipo": "produto_pronto"},
    {"nome": "Banana Split", "preco": 18.00, "categoria": "Sobremesas", "tipo": "produto_pronto"}
]

prato_principal = [
    {"nome": "Arroz carreteiro", "preco": 30.00, "categoria": "Pratos principais", "tipo": "produto_pronto"},
    {"nome": "Lasanha bolonhesa", "preco": 28.00, "categoria": "Pratos principais", "tipo": "produto_pronto"},
    {"nome": "Parmegiana", "preco": 35.00, "categoria": "Pratos principais", "tipo": "produto_pronto"}
]

entrada = [
    {"nome": "Salada Caesar", "preco": 19.99, "categoria": "Entradas", "tipo": "produto_pronto"},
    {"nome": "Bruschetta", "preco": 28.00, "categoria": "Entradas", "tipo": "produto_pronto"},
    {"nome": "Salada Americana", "preco": 35.00, "categoria": "Entradas", "tipo": "produto_pronto"}
]

bebida = [
    {"nome": "Coca-cola", "preco": 8.00, "categoria": "Bebidas", "tipo": "produto_pronto"},
    {"nome": "Suco", "preco": 7.00, "categoria": "Bebidas", "tipo": "produto_pronto"},
    {"nome": "Água", "preco": 5.00, "categoria": "Bebidas", "tipo": "produto_pronto"}
]

categoria = Categoria(
    sobremesa,
    prato_principal,
    entrada,
    bebida
)
