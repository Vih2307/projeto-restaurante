"""Confere se o .env está certo e se o Neon e o Firebase respondem.

Uso:  python verificar_configuracao.py
Nenhum dado é alterado e nenhum e-mail é enviado.
"""
import os

from dotenv import load_dotenv

import autenticacao
import banco
from autenticacao import ErroAutenticacao
from banco import BancoErro


def mostrar(ok, texto, detalhe=""):
    print(("[OK]   " if ok else "[ERRO] ") + texto)
    if detalhe:
        print("       " + detalhe)
    return ok


def variavel_definida(nome, ajuda):
    return mostrar(bool(os.getenv(nome, "").strip()), nome + " definido no .env", "" if os.getenv(nome, "").strip() else ajuda)


def verificar():
    load_dotenv()
    resultados = []

    print("1) Variáveis do arquivo .env")
    resultados.append(variavel_definida("CHAVE_SECRETA", "Gere uma com: python -c \"import secrets; print(secrets.token_hex(32))\""))
    resultados.append(variavel_definida("DATABASE_URL", "Copie o endereço de conexão no painel do Neon (botão Connect)."))
    resultados.append(variavel_definida("FIREBASE_API_KEY", "Firebase > Configurações do projeto > Geral > Chave de API da Web."))
    tem_credencial = bool(os.getenv("FIREBASE_CREDENCIAIS", "").strip() or os.getenv("FIREBASE_CREDENCIAIS_JSON", "").strip())
    resultados.append(mostrar(
        tem_credencial,
        "Credenciais da conta de serviço definidas (FIREBASE_CREDENCIAIS)",
        "" if tem_credencial else "Firebase > Configurações do projeto > Contas de serviço > Gerar nova chave privada.",
    ))

    print("\n2) Banco Neon")
    try:
        versao = banco.testar_conexao()
        resultados.append(mostrar(True, "Conectou ao Neon e a tabela 'usuarios' está pronta", versao))
    except BancoErro as erro:
        resultados.append(mostrar(False, "Conexão com o Neon", str(erro)))

    print("\n3) Firebase")
    try:
        autenticacao.testar_credenciais_admin()
        resultados.append(mostrar(True, "Conta de serviço aceita pelo Firebase"))
    except ErroAutenticacao as erro:
        resultados.append(mostrar(False, "Conta de serviço do Firebase", erro.mensagem))
    try:
        autenticacao.testar_chave_api()
        resultados.append(mostrar(True, "Chave de API aceita e login por e-mail/senha ativado"))
    except ErroAutenticacao as erro:
        resultados.append(mostrar(False, "Chave de API do Firebase", erro.mensagem))

    print()
    if all(resultados):
        print("Tudo certo. Cadastre o primeiro usuário com: python cadastrar_usuario.py")
    else:
        print("Corrija os itens marcados com [ERRO] e rode este arquivo de novo.")
    return all(resultados)


if __name__ == "__main__":
    raise SystemExit(0 if verificar() else 1)
