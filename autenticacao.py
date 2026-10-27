"""Integração com o Firebase Authentication.

O Firebase guarda e confere as senhas e envia o e-mail de recuperação.
Este módulo usa duas partes dele:

- API REST (com a "Chave de API da Web"): conferir e-mail e senha no login e pedir
  o envio do e-mail de recuperação.
- Firebase Admin SDK (com a conta de serviço): validar o token recebido, criar contas
  e conferir se uma sessão antiga continua válida.
"""
import json
import os
import threading

import firebase_admin
import requests
from firebase_admin import auth, credentials
from firebase_admin.exceptions import FirebaseError

URL_LOGIN = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
URL_RECUPERACAO = "https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode"
TEMPO_LIMITE = 10  # segundos esperando o Firebase responder

# Erros do Firebase que significam "e-mail ou senha incorretos".
ERROS_CREDENCIAIS = {
    "EMAIL_NOT_FOUND",
    "INVALID_PASSWORD",
    "INVALID_LOGIN_CREDENTIALS",
    "INVALID_EMAIL",
    "MISSING_PASSWORD",
}


class ErroAutenticacao(Exception):
    """Falha de autenticação. O atributo `tipo` diz o que aconteceu:

    credenciais        e-mail ou senha incorretos
    desativada         conta desativada no Firebase
    muitas_tentativas  o Firebase bloqueou a conta temporariamente
    configuracao       chave de API ou credenciais do Firebase erradas
    indisponivel       sem comunicação com o Firebase
    """

    def __init__(self, tipo, mensagem):
        super().__init__(mensagem)
        self.tipo = tipo
        self.mensagem = mensagem


_trava = threading.Lock()


def _app():
    """Inicia o Firebase Admin SDK uma única vez."""
    try:
        return firebase_admin.get_app()
    except ValueError:
        pass
    with _trava:
        try:
            return firebase_admin.get_app()
        except ValueError:
            pass
        conteudo = os.getenv("FIREBASE_CREDENCIAIS_JSON", "").strip()
        caminho = os.getenv("FIREBASE_CREDENCIAIS", "").strip()
        try:
            if conteudo:
                credencial = credentials.Certificate(json.loads(conteudo))
            elif caminho:
                credencial = credentials.Certificate(caminho)
            else:
                raise ErroAutenticacao(
                    "configuracao",
                    "Configure FIREBASE_CREDENCIAIS (caminho do arquivo JSON da conta de serviço) no .env.",
                )
        except (ValueError, OSError) as erro:
            raise ErroAutenticacao(
                "configuracao",
                "Não foi possível ler as credenciais do Firebase: " + str(erro),
            ) from erro
        return firebase_admin.initialize_app(credencial, {"httpTimeout": TEMPO_LIMITE})


def _chave_api():
    chave = os.getenv("FIREBASE_API_KEY", "").strip()
    if not chave:
        raise ErroAutenticacao("configuracao", "Configure FIREBASE_API_KEY (Chave de API da Web) no .env.")
    return chave


def _codigo_do_erro(resposta):
    """Extrai o código do erro de uma resposta da API REST (ex.: INVALID_PASSWORD)."""
    try:
        erro = resposta.json().get("error", {})
    except ValueError:
        return "", ""
    mensagem = str(erro.get("message", ""))
    return mensagem.split(" : ")[0].strip(), mensagem


def _chamar(url, corpo, cabecalhos=None):
    try:
        return requests.post(
            url,
            params={"key": _chave_api()},
            json=corpo,
            headers=cabecalhos or {},
            timeout=TEMPO_LIMITE,
        )
    except requests.RequestException as erro:
        raise ErroAutenticacao("indisponivel", "Não foi possível falar com o Firebase.") from erro


def _erro_da_resposta(resposta):
    codigo, completa = _codigo_do_erro(resposta)
    if codigo in ERROS_CREDENCIAIS:
        return ErroAutenticacao("credenciais", "E-mail ou senha incorretos.")
    if codigo == "USER_DISABLED":
        return ErroAutenticacao("desativada", "Conta desativada.")
    if codigo == "TOO_MANY_ATTEMPTS_TRY_LATER":
        return ErroAutenticacao("muitas_tentativas", "Muitas tentativas. Tente novamente mais tarde.")
    if resposta.status_code in (400, 403) or "API key" in completa:
        return ErroAutenticacao(
            "configuracao",
            "O Firebase recusou a chave de API (" + (completa or str(resposta.status_code)) + ").",
        )
    return ErroAutenticacao("indisponivel", "O Firebase respondeu com erro " + str(resposta.status_code) + ".")


def entrar(email, senha):
    """Confere e-mail e senha no Firebase.

    Devolve {"uid", "email", "iat"}, onde `iat` é o momento (segundos) em que o Firebase
    emitiu o token. Esse valor serve depois para saber se a sessão foi invalidada.
    """
    resposta = _chamar(URL_LOGIN, {"email": email, "password": senha, "returnSecureToken": True})
    if resposta.status_code != 200:
        raise _erro_da_resposta(resposta)
    try:
        token = resposta.json()["idToken"]
        dados = auth.verify_id_token(token, app=_app(), clock_skew_seconds=10)
    except ErroAutenticacao:
        raise
    except (KeyError, ValueError, FirebaseError) as erro:
        raise ErroAutenticacao(
            "configuracao",
            "O token do Firebase não passou na verificação. Confira se FIREBASE_API_KEY e o "
            "arquivo da conta de serviço são do mesmo projeto. (" + str(erro) + ")",
        ) from erro
    return {"uid": dados["uid"], "email": dados.get("email", email), "iat": dados["iat"]}


def enviar_recuperacao(email):
    """Pede ao Firebase que envie o e-mail com o link para redefinir a senha."""
    corpo = {"requestType": "PASSWORD_RESET", "email": email}
    resposta = _chamar(URL_RECUPERACAO, corpo, {"X-Firebase-Locale": "pt-BR"})
    if resposta.status_code == 200:
        return
    codigo, _ = _codigo_do_erro(resposta)
    if codigo == "EMAIL_NOT_FOUND":
        return  # não revelamos se o e-mail existe
    raise _erro_da_resposta(resposta)


def conta_ainda_valida(uid, iat):
    """Confere se uma sessão iniciada com o token emitido em `iat` continua válida.

    A sessão deixa de valer quando a conta foi apagada, desativada ou teve a senha
    redefinida depois do login (o Firebase registra esse momento em
    tokens_valid_after_timestamp).
    """
    try:
        usuario = auth.get_user(uid, app=_app())
    except auth.UserNotFoundError:
        return False
    except ErroAutenticacao:
        raise
    except (FirebaseError, ValueError) as erro:
        raise ErroAutenticacao("indisponivel", "Não foi possível consultar o Firebase.") from erro
    if usuario.disabled:
        return False
    valido_apos = (usuario.tokens_valid_after_timestamp or 0) / 1000
    return iat >= valido_apos


def buscar_conta_por_email(email):
    """Devolve a conta do Firebase com esse e-mail, ou None."""
    try:
        return auth.get_user_by_email(email, app=_app())
    except auth.UserNotFoundError:
        return None
    except ErroAutenticacao:
        raise
    except (FirebaseError, ValueError) as erro:
        raise ErroAutenticacao("indisponivel", "Não foi possível consultar o Firebase: " + str(erro)) from erro


def criar_conta(email, senha, nome):
    """Cria uma conta no Firebase e devolve o uid."""
    try:
        return auth.create_user(email=email, password=senha, display_name=nome, app=_app()).uid
    except ErroAutenticacao:
        raise
    except (FirebaseError, ValueError) as erro:
        raise ErroAutenticacao("indisponivel", "Não foi possível criar a conta no Firebase: " + str(erro)) from erro


def remover_conta(uid):
    try:
        auth.delete_user(uid, app=_app())
    except (FirebaseError, ValueError, ErroAutenticacao):
        pass


def testar_credenciais_admin():
    """Usada pelo verificar_configuracao.py: confirma que a conta de serviço funciona."""
    try:
        auth.list_users(max_results=1, app=_app())
    except ErroAutenticacao:
        raise
    except (FirebaseError, ValueError) as erro:
        raise ErroAutenticacao("configuracao", "A conta de serviço foi recusada: " + str(erro)) from erro


def testar_chave_api():
    """Usada pelo verificar_configuracao.py: confirma que a chave de API é aceita.

    Tenta um login com dados que não existem. Se o Firebase responder "credenciais
    incorretas", a chave está funcionando.
    """
    resposta = _chamar(
        URL_LOGIN,
        {"email": "teste-de-configuracao@example.com", "password": "senha-qualquer-123", "returnSecureToken": True},
    )
    if resposta.status_code == 200:
        return
    erro = _erro_da_resposta(resposta)
    if erro.tipo != "credenciais":
        raise erro
