import json
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash


ARQUIVO_USUARIOS = Path(__file__).parent / "dados" / "usuarios.json"


class Usuario:
    def __init__(self, nome, email, senha):
        self.nome = nome
        self.email = email
        self.senha = senha
        self.versao = 1
        self.codigo = ""
        self.validade_codigo = 0
        self.tentativas = 0
        self.ultimo_envio = 0

    def verificar_senha(self, senha):
        return check_password_hash(self.senha, senha)

    def alterar_senha(self, nova_senha):
        self.senha = generate_password_hash(nova_senha)
        self.versao += 1
        self.codigo = ""
        self.validade_codigo = 0
        self.tentativas = 0


def carregar_usuarios():
    usuarios = []
    if ARQUIVO_USUARIOS.exists():
        with open(ARQUIVO_USUARIOS, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        for dado in dados:
            usuario = Usuario(dado["nome"], dado["email"], dado["senha"])
            usuario.versao = dado["versao"]
            usuario.codigo = dado["codigo"]
            usuario.validade_codigo = dado["validade_codigo"]
            usuario.tentativas = dado["tentativas"]
            usuario.ultimo_envio = dado["ultimo_envio"]
            usuarios.append(usuario)
    return usuarios


def salvar_usuarios(usuarios):
    dados = []
    for usuario in usuarios:
        dados.append({
            "nome": usuario.nome,
            "email": usuario.email,
            "senha": usuario.senha,
            "versao": usuario.versao,
            "codigo": usuario.codigo,
            "validade_codigo": usuario.validade_codigo,
            "tentativas": usuario.tentativas,
            "ultimo_envio": usuario.ultimo_envio
        })
    ARQUIVO_USUARIOS.parent.mkdir(exist_ok=True)
    temporario = ARQUIVO_USUARIOS.with_suffix(".tmp")
    with open(temporario, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=4)
    temporario.replace(ARQUIVO_USUARIOS)


def buscar_usuario(usuarios, email):
    for usuario in usuarios:
        if usuario.email == email:
            return usuario
    return None


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
