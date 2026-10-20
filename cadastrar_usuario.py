from getpass import getpass
from werkzeug.security import generate_password_hash
from usuario import Usuario, carregar_usuarios, salvar_usuarios, buscar_usuario
from usuario import senha_valida, email_valido


def cadastrar_usuario():
    usuarios = carregar_usuarios()
    nome = input("Nome: ").strip()
    email = input("E-mail: ").strip().lower()
    senha = getpass("Senha com pelo menos 8 caracteres, letras e números: ")
    confirmacao = getpass("Confirme a senha: ")

    if len(nome) < 2 or len(nome) > 100:
        print("Informe um nome entre 2 e 100 caracteres.")
    elif not email_valido(email):
        print("E-mail inválido.")
    elif buscar_usuario(usuarios, email) is not None:
        print("E-mail já cadastrado.")
    elif not senha_valida(senha):
        print("Senha inválida.")
    elif senha != confirmacao:
        print("As senhas não são iguais.")
    else:
        usuarios.append(Usuario(nome, email, generate_password_hash(senha)))
        salvar_usuarios(usuarios)
        print("Usuário cadastrado.")


if __name__ == "__main__":
    cadastrar_usuario()
