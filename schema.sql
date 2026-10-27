-- Tabela de funcionários do Restaurante BKV (banco Neon / PostgreSQL).
-- O sistema cria esta tabela sozinho na primeira conexão; este arquivo existe
-- para quem preferir executá-la manualmente no "SQL Editor" do Neon.
--
-- A senha não é guardada aqui. Quem guarda e confere as senhas é o Firebase
-- Authentication; esta tabela só diz quem tem permissão de usar o sistema.

CREATE TABLE IF NOT EXISTS usuarios (
    id                        BIGSERIAL PRIMARY KEY,
    firebase_uid              TEXT        NOT NULL UNIQUE,  -- identificador da conta no Firebase
    nome                      TEXT        NOT NULL,
    email                     TEXT        NOT NULL UNIQUE,  -- sempre em letras minúsculas
    ativo                     BOOLEAN     NOT NULL DEFAULT TRUE,
    criado_em                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    ultimo_login              TIMESTAMPTZ,
    ultimo_envio_recuperacao  TIMESTAMPTZ
);

-- Para bloquear um funcionário sem apagar o histórico:
--   UPDATE usuarios SET ativo = FALSE WHERE email = 'funcionario@exemplo.com';
