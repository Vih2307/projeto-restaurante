from getpass import getpass

from dotenv import load_dotenv

import autenticacao
import banco
from autenticacao import ErroAutenticacao
from banco import BancoErro
from usuario import email_valido, nome_valido, senha_valida


def cadastrar_usuario():
    """Cadastra um funcionário: conta no Firebase (senha) + registro no Neon (permissão)."""
    load_dotenv()
    nome = input("Nome: ").strip()
    email = input("E-mail: ").strip().lower()

    if not nome_valido(nome):
        print("Informe um nome entre 2 e 100 caracteres.")
        return
    if not email_valido(email):
        print("E-mail inválido.")
        return

    try:
        if banco.buscar_usuario_por_email(email) is not None:
            print("E-mail já cadastrado no sistema.")
            return

        existente = autenticacao.buscar_conta_por_email(email)
        if existente is not None:
            # A conta já existe no Firebase (por exemplo, criada pelo console).
            resposta = input(
                "Esse e-mail já existe no Firebase. Liberar o acesso dele ao sistema, "
                "sem mudar a senha? (s/n): "
            ).strip().lower()
            if resposta != "s":
                print("Nada foi alterado.")
                return
            banco.criar_usuario(existente.uid, nome, email)
            print("Acesso liberado. A senha continua a mesma da conta do Firebase.")
            return

        senha = getpass("Senha com pelo menos 8 caracteres, letras e números: ")
        confirmacao = getpass("Confirme a senha: ")
        if not senha_valida(senha):
            print("Senha inválida.")
            return
        if senha != confirmacao:
            print("As senhas não são iguais.")
            return

        uid = autenticacao.criar_conta(email, senha, nome)
        try:
            banco.criar_usuario(uid, nome, email)
        except BancoErro:
            # Evita deixar uma conta no Firebase sem registro no Neon.
            autenticacao.remover_conta(uid)
            raise
        print("Usuário cadastrado.")
    except (BancoErro, ErroAutenticacao) as erro:
        print("Não foi possível cadastrar:", erro)
        print("Rode 'python verificar_configuracao.py' para encontrar o problema.")


if __name__ == "__main__":
    cadastrar_usuario()
