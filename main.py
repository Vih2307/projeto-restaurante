from mesa import Mesa
from pedido import Pedido
from categoria import categoria
from caixa import Caixa

mesas = [
    Mesa("Livre", 1, False),
    Mesa("Livre", 2, False),
    Mesa("Livre", 3, False),
    Mesa("Livre", 4, False),
    Mesa("Livre", 5, False)
]

pedidos = []

caixa = Caixa()
caixa.abrir_caixa()

numero_pedido = 1

cardapio = (
    categoria.entrada
    + categoria.prato_principal
    + categoria.bebida
    + categoria.sobremesa
)


while True:

    print("\n==============================")
    print("      SISTEMA RESTAURANTE")
    print("==============================")
    print("1 - Novo atendimento")
    print("2 - Ver mesas")
    print("3 - Ver pedidos")
    print("4 - Fechar conta")
    print("5 - Ver caixa")
    print("0 - Encerrar sistema")

    opcao = input("\nEscolha uma opção: ")

    if opcao == "1":

        print("\n----- MESAS -----")

        for mesa in mesas:
            print(
                f"Mesa {mesa.numero} - {mesa.status}"
            )

        numero_mesa = int(
            input("\nInforme a mesa do cliente: ")
        )

        mesa_escolhida = None

        for mesa in mesas:

            if mesa.numero == numero_mesa:
                mesa_escolhida = mesa


        if mesa_escolhida is None:

            print("Mesa não encontrada.")

        elif mesa_escolhida.status != "Livre":

            print("Essa mesa está ocupada.")

        else:

            mesa_escolhida.ocupar()

            pedido = Pedido(
                numero_pedido,
                mesa_escolhida
            )

            print(
                f"\nPedido {numero_pedido} criado."
            )

            while True:

                print("\n==============================")
                print("           CARDÁPIO")
                print("==============================")

                for i, produto in enumerate(
                    cardapio,
                    start=1
                ):

                    print(
                        f"{i} - "
                        f"{produto['nome']} - "
                        f"R$ {produto['preco']:.2f}"
                    )

                print("0 - Finalizar pedido")

                escolha = int(
                    input("\nProduto: ")
                )


                if escolha == 0:
                    break


                if escolha > 0 and escolha <= len(cardapio):

                    produto = cardapio[
                        escolha - 1
                    ]

                    quantidade = int(
                        input("Quantidade: ")
                    )

                    pedido.adicionar_item(
                        produto["nome"],
                        produto["preco"],
                        quantidade
                    )

                    print(
                        f"{produto['nome']} adicionado."
                    )

                    print(
                        f"Total atual: "
                        f"R$ {pedido.calcular_total():.2f}"
                    )

                else:

                    print("Produto inválido.")


            if len(pedido.itens) > 0:

                pedido.atualizar_status(
                    "Em preparo"
                )

                pedidos.append(pedido)

                print("\nPedido registrado!")

                pedido.mostrar_pedido()

                numero_pedido += 1

            else:

                print("Pedido cancelado.")

                mesa_escolhida.liberar()

    elif opcao == "2":

        print("\n----- MESAS -----")

        for mesa in mesas:

            print(
                f"Mesa {mesa.numero} - "
                f"{mesa.status}"
            )

    elif opcao == "3":

        print("\n----- PEDIDOS -----")

        if len(pedidos) == 0:

            print("Nenhum pedido registrado.")

        else:

            for pedido in pedidos:

                print(
                    f"\nPedido {pedido.numero}"
                )

                print(
                    f"Mesa: {pedido.mesa.numero}"
                )

                print(
                    f"Status: {pedido.status}"
                )

                print(
                    f"Total: "
                    f"R$ {pedido.calcular_total():.2f}"
                )

    elif opcao == "4":

        print("\n----- FECHAR CONTA -----")

        for pedido in pedidos:

            if pedido.status != "Finalizado":

                print(
                    f"Pedido {pedido.numero} - "
                    f"Mesa {pedido.mesa.numero} - "
                    f"R$ {pedido.calcular_total():.2f}"
                )


        numero = int(
            input("\nNúmero do pedido: ")
        )

        pedido_encontrado = None


        for pedido in pedidos:

            if (
                pedido.numero == numero
                and pedido.status != "Finalizado"
            ):

                pedido_encontrado = pedido


        if pedido_encontrado is None:

            print("Pedido não encontrado.")

        else:

            pedido_encontrado.mesa.pedir_conta()

            print("\n----- CONTA -----")

            pedido_encontrado.mostrar_pedido()

            print("\nForma de pagamento:")

            print("1 - Dinheiro")
            print("2 - PIX")
            print("3 - Débito")
            print("4 - Crédito")

            pagamento = input(
                "\nEscolha: "
            )


            if pagamento == "1":
                forma = "Dinheiro"

            elif pagamento == "2":
                forma = "PIX"

            elif pagamento == "3":
                forma = "Débito"

            elif pagamento == "4":
                forma = "Crédito"

            else:
                forma = "Não informado"


            pedido_encontrado.escolher_pagamento(
                forma
            )

            caixa.registrar_venda(
                pedido_encontrado
            )

            pedido_encontrado.mesa.liberar()

            print("\nConta fechada com sucesso!")

            print(
                f"Pagamento: {forma}"
            )

    elif opcao == "5":

        caixa.gerar_saldo_diario()

    elif opcao == "0":

        caixa.fechar_caixa()

        print("\nSistema encerrado.")

        break

    else:

        print("Opção inválida.")    