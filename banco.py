"""Acesso ao banco de dados Neon (PostgreSQL).

Guarda a lista de funcionários autorizados a usar o sistema. A senha NÃO fica
aqui: quem guarda e confere as senhas é o Firebase Authentication.
"""
import os
import threading
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row


class BancoErro(Exception):
    """Falha ao falar com o banco (configuração, rede ou consulta)."""


# Mesmo conteúdo do arquivo schema.sql.
CRIAR_TABELA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id                        BIGSERIAL PRIMARY KEY,
    firebase_uid              TEXT        NOT NULL UNIQUE,
    nome                      TEXT        NOT NULL,
    email                     TEXT        NOT NULL UNIQUE,
    ativo                     BOOLEAN     NOT NULL DEFAULT TRUE,
    criado_em                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    ultimo_login              TIMESTAMPTZ,
    ultimo_envio_recuperacao  TIMESTAMPTZ
)
"""

_tabela_pronta = False
_trava = threading.Lock()


def _url():
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise BancoErro("Configure DATABASE_URL no arquivo .env (endereço de conexão do Neon).")
    return url


@contextmanager
def conexao():
    """Abre uma conexão, confirma (commit) ao final e fecha.

    Na primeira conexão do programa, cria a tabela de usuários se ela ainda não existir.
    """
    global _tabela_pronta
    try:
        with psycopg.connect(_url(), row_factory=dict_row, connect_timeout=10) as conn:
            if not _tabela_pronta:
                with _trava:
                    if not _tabela_pronta:
                        conn.execute(CRIAR_TABELA)
                        _tabela_pronta = True
            yield conn
    except psycopg.Error as erro:
        raise BancoErro("Não foi possível usar o banco Neon: " + str(erro).strip().splitlines()[0]) from erro


def testar_conexao():
    """Usada pelo verificar_configuracao.py. Devolve a versão do PostgreSQL."""
    with conexao() as conn:
        return conn.execute("SELECT version() AS versao").fetchone()["versao"]


def buscar_usuario_por_email(email):
    with conexao() as conn:
        return conn.execute(
            "SELECT id, firebase_uid, nome, email, ativo FROM usuarios WHERE email = %s",
            (email,),
        ).fetchone()


def buscar_usuario_por_uid(uid):
    with conexao() as conn:
        return conn.execute(
            "SELECT id, firebase_uid, nome, email, ativo FROM usuarios WHERE firebase_uid = %s",
            (uid,),
        ).fetchone()


def criar_usuario(uid, nome, email):
    with conexao() as conn:
        conn.execute(
            "INSERT INTO usuarios (firebase_uid, nome, email) VALUES (%s, %s, %s)",
            (uid, nome, email),
        )


def registrar_login(uid):
    with conexao() as conn:
        conn.execute("UPDATE usuarios SET ultimo_login = now() WHERE firebase_uid = %s", (uid,))


def reservar_envio_recuperacao(email, intervalo_segundos=60):
    """Marca o envio de um e-mail de recuperação, se for permitido.

    Devolve True quando o e-mail pertence a um funcionário ativo e já passou o intervalo
    mínimo desde o último pedido. Devolve False caso contrário (e-mail desconhecido,
    conta desativada ou pedido recente). A conferência e a marcação acontecem em um
    único comando, então dois pedidos ao mesmo tempo não passam juntos.
    """
    with conexao() as conn:
        linha = conn.execute(
            """
            UPDATE usuarios
               SET ultimo_envio_recuperacao = now()
             WHERE email = %s
               AND ativo
               AND (ultimo_envio_recuperacao IS NULL
                    OR ultimo_envio_recuperacao < now() - make_interval(secs => %s))
            RETURNING id
            """,
            (email, intervalo_segundos),
        ).fetchone()
        return linha is not None
