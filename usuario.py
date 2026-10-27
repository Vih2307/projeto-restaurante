"""Validações de dados dos usuários.

Os usuários em si ficam no banco Neon (banco.py) e as senhas no Firebase
(autenticacao.py). Aqui ficam apenas as regras de formato.
"""


def senha_valida(senha):
    if not isinstance(senha, str) or len(senha) < 8 or len(senha) > 128:
        return False
    tem_letra = False
    tem_numero = False
    for caractere in senha:
        if caractere.isalpha():
            tem_letra = True
        if caractere.isdigit():
            tem_numero = True
    return tem_letra and tem_numero


def email_valido(email):
    if not isinstance(email, str) or len(email) > 254 or " " in email:
        return False
    for caractere in email:
        if caractere.isspace():
            return False
    partes = email.split("@")
    if len(partes) != 2:
        return False
    return bool(partes[0]) and "." in partes[1] and not partes[1].startswith(".") and not partes[1].endswith(".")


def nome_valido(nome):
    return isinstance(nome, str) and 2 <= len(nome.strip()) <= 100
